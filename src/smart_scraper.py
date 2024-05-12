""" Scrape the SF government website using the Grok and Llama3 with SmartScraperGraph.

The main functionality is provided by the `main()` function, which:
1. Starts with a set of initial URLs to visit.
2. For each URL, it checks if the URL is valid and has not been visited before.
3. If the URL is an internal link (starting with "https://www.sf.gov/topics"), 
    it uses the `link_prompt` to scrape the page for additional URLs and their 
    descriptions.
4. If the URL is an external link, it uses the `external_link_prompt` to scrape 
    relevant information from the page.
5. The scraped URLs and their descriptions are stored in the 
    `visited_url_descriptions` dictionary.
6. If a URL is a redirect, the redirect URL is stored in the `redirected_urls` 
    dictionary, and the redirect URL is added to the `urls_to_visit` dictionary.
7. The process continues until all URLs in `urls_to_visit` have been visited.
8. Finally, the `visited_url_descriptions` dictionary is saved to a JSON file named 
    "data/visited_urls.json".

The module uses the SmartScraperGraph from the scrapegraphai library to perform the 
actual scraping. The configuration for the SmartScraperGraph is obtained using the 
`get_config()` function, which loads the necessary API keys from environment variables.

The module also includes utility functions:
- `is_url_valid(url)`: Checks if a URL returns a 200 status code.
- `is_url_redirect(url)`: Checks if a URL is a redirect.
- `retry_with_exponential_backoff()`: A decorator that retries a function with 
    exponential backoff if an exception is raised.

To use this module, ensure that the required dependencies are installed and the 
    necessary environment variables are set. Then, simply run the `main()` function 
    to start the scraping process.
"""

from dotenv import find_dotenv, load_dotenv
from functools import wraps
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info
from typing import Any, Callable, Dict, TypeVar
import json
import os
import requests
import time

from loguru import logger

load_dotenv(find_dotenv())

# Type variable for generic type hinting.
T = TypeVar("T")

# Load the API keys from the environment.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # If using Groq.


# Requires Ollama to be running in a Docker container .
# ```
#
def get_config(model: str) -> Dict[str, Any]:
    """Get the configuration for the SmartScraperGraph.

     Uses the Groq model for the LLM and the Ollama model for the embeddings.

     The embeddings model is required to run the SmartScraperGraph using Groq.
     The embeddig model used is: "ollama/nomic-embed-text"
     https://ollama.com/library/nomic-embed-text

     Requires pulling the `nomic-embed-text` model using the ollama docker container.
     ```
     # First, pull the ollama docker container.
     docker pull ollama/ollama

     # Then, ensure the model is running in a Docker container on port 11434.
     docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

    # Finally, use the ollama docker container to pull the embedding model.
     docker exec -it ollama ollama pull nomic-embed-text
     ```

     Args:
         model: The Groq model to use for the SmartScraperGraph.  See available models:
             https://console.groq.com/docs/models

     Returns:
         The configuration for the SmartScraperGraph.
    """
    return {
        "llm": {
            "model": "groq/llama3-8b-8192",
            "api_key": GROQ_API_KEY,
            "temperature": 0.5,
        },
        "embeddings": {
            "model": "ollama/nomic-embed-text",
            "temperature": 0.0,
            "base_url": "http://localhost:11434",
        },
        "headless": False,
    }


graph_config = get_config(model="groq/llama3-8b-8192")


def is_url_valid(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        # Send a HEAD request to the URL
        response = requests.head(url, allow_redirects=True)
        # Check if the HTTP status code is OK (200 range)
        if response.ok:
            return True
        else:
            return False
    except requests.RequestException as e:
        # Handle exceptions that may occur during the request
        logger.error(f"An error occurred validating {url=}: {e}")
        return False


def is_url_redirect(url):
    try:
        response = requests.head(url, allow_redirects=True, verify=False)
    except requests.RequestException as e:
        logger.error(f"An error occurred validating {url=}: {e}")
        raise e

    return url != response.url


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[T], T]:
    """Retry decorator with exponential backoff.

    This decorator can be applied to download methods in ingestor classes to handle
    failed downloads by retrying with exponential backoff. It retries the decorated
    function if an exception specified in the `exceptions` argument is raised, up to
    a maximum number of retries defined by `max_retries`. The delay between retries
    increases exponentially based on the `initial_delay` and `backoff_factor`.

    Args:
        max_retries: Maximum number of retries.
        initial_delay: Initial delay in seconds before retrying.
        backoff_factor: Factor by which the delay increases with each retry.
        exceptions: Tuple of exceptions to catch and retry on.

    Returns:
        Decorator function.

    Example usage:
        @BaseIngestor.retry_with_exponential_backoff(
            max_retries=3, initial_delay=1.0, backoff_factor=2.0
        )
        def download(self, data_source...) -> Generator[Dict[str, Any], None, None]:
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            err_msg = f"Max retries reached ({max_retries}). Raising exception"
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"{err_msg}: {e}")
                        raise e
                    else:
                        logger.warning(
                            f"Attempt {attempt + 1} failed. "
                            f"Retrying in {delay:.2f} seconds. Error: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor

        return wrapper

    return decorator  # type: ignore


# ************************************************
# Create the SmartScraperGraph instance and run it
# ************************************************

root_url = "https://www.sf.gov/"
topic_url = "https://www.sf.gov/topics"

url_template = """\
    {url: description}
"""

link_prompt = f"""\
Give me all the URLs for all the services on this webpage starting with \
{topic_url} and a description of that link. \
Return it in this JSON format: {url_template}
"""

external_link_prompt = (
    "Provide the relevant information for this website that would be useful for "
    "a chatbot to answer questions about it."
)


@retry_with_exponential_backoff()
def smart_scrape(url: str, prompt: str):
    return SmartScraperGraph(prompt=prompt, source=url, config=graph_config).run()


def main():
    """Run the SmartScraperGraph on the San Francisco government website as a script.

    Saves the visited URLs and their descriptions to a JSON file:
        "data/visited_urls.json"
    """
    visited_urls = set()  # Ones we have already scraped, whether saved or not.
    visited_url_descriptions: dict[str, Any] = {}  # Ones we want to keep.
    urls_to_visit: dict[str, Any] = {
        root_url: "The main page of the San Francisco government website."
    }
    redirected_urls: dict[str, str] = {}

    while urls_to_visit:
        url = list(urls_to_visit.keys())[0]
        if url in visited_urls or not is_url_valid(url):
            visited_urls.add(url)
            continue  # Already scraped this URL or it does not return a 200.

        description = urls_to_visit.pop(url)
        visited_url_descriptions[url] = description
        # Use the redirect URL if it is different from the original URL.
        redirected_url = ""
        if is_url_redirect(url):
            redirected_url = requests.head(url, allow_redirects=True, verify=False).url
            redirected_urls[url] = redirected_url
            urls_to_visit[redirected_url] = ""  # No description means not internal.
            urls_to_visit.pop(url, None)
        if url == root_url or url.startswith(topic_url) and description:
            # This is sf.gov or an internal link to sf.gov/topics/...
            internal = True
            prompt = link_prompt
        else:
            internal = False
            prompt = external_link_prompt

        result = {}
        try:
            logger.info(f"Scraping {url}")
            result = smart_scrape(url, prompt)
        except Exception as e:
            logger.warning(
                f"Failed to scrape {url}. {prettify_exec_info(e)}"  # type: ignore
            )
            continue

        if not isinstance(result, dict):
            logger.warning(f"Failed to scrape {url}. {result}")
            continue

        visited_url_count = len(visited_url_descriptions)
        for link, description in result.items():
            if not link.startswith("http"):
                continue  # Skip non-URLs.
            if link in redirected_urls:
                forwarded_url = redirected_urls[link]
                description += f" [{forwarded_url}]({forwarded_url})"
            logger.info(f"{link=}, {description=}")
            visited_url_descriptions[link] = description
            if link not in visited_urls and link not in urls_to_visit and internal:
                # Only add links found in topics.
                urls_to_visit[link] = description

        logger.info(f"Size of visited URLs: {visited_url_count}")
        logger.info(f"Size of URLs to visit: {len(urls_to_visit)}")

    with open("data/visited_urls.json", "w") as f:
        json.dump(visited_url_descriptions, f, indent=2)
