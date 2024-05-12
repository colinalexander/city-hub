from dotenv import load_dotenv
from functools import wraps
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info
from typing import Any, Callable, Dict, TypeVar
import json
import os
import requests
import time

from loguru import logger

load_dotenv()

T = TypeVar("T")

openai_key = os.getenv("OPENAI_APIKEY")

graph_config = {
    "llm": {
        "api_key": openai_key,
        "model": "gpt-3.5-turbo",
    },
}


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

    return decorator


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
        logger.warning(f"Failed to scrape {url}. {prettify_exec_info(e)}")
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
