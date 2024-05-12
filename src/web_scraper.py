from functools import wraps
from typing import Any, Callable, Dict, Generator, Optional, TypeVar
from urllib.parse import urljoin, urlparse, urlunparse
import requests
import time

from bs4 import BeautifulSoup as Soup
from dotenv import find_dotenv, load_dotenv
from loguru import logger
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader

load_dotenv(find_dotenv())

# Type variable for generic type hinting.
T = TypeVar("T")

# HTML parser used by BeautifulSoup.
HTML_PARSER = "html5lib"  

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

#BaseIngestor.retry_with_exponential_backoff(
#    max_retries=3, initial_delay=1.0, backoff_factor=2.0
#)
def make_request(url: str, timeout: float = 10.0) -> requests.Response:
    """Make an HTTP request with retry and delay.

    This function makes an HTTP GET request to the specified URL.

    Args:
        url: The URL to where the request is made.
        timeout: The request timeout in seconds.

    Returns:
        The response object from the request.

    Raises:
        requests.exceptions.RequestException: If the request fails after all retries.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def parse_html(html: str) -> Soup:
    """Parse HTML content using BeautifulSoup.

    Uses the 'html5lib' parser to parse the HTML content.

    Args:
        html: The HTML content to parse.

    Returns:
        A BeautifulSoup object representing the parsed HTML content.
    """
    return Soup(markup=html, features=HTML_PARSER)

def get_base_url(soup: Soup) -> str:
    """Extract the base URL from a BeautifulSoup object.

    Args:
        soup: The BeautifulSoup object representing the parsed HTML content.

    Returns:
        The base URL.
    """
    # Try to find a base tag
    base_tag = soup.find('base')
    if base_tag and base_tag.get('href'):
        base_url = base_tag['href']
    else:
        # Fallback to the scheme and netloc from the original URL
        parsed_url = urlparse(url)
        base_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
    return base_url if isinstance(base_url, str) else base_url[0]


url = "https://www.sf.gov"
parsed_url = urlparse(url)
base_url = urlunparse((parsed_url.scheme, parsed_url.netloc, "", "", "", ""))

loader = RecursiveUrlLoader(
    url=url, max_depth=2, extractor=lambda x: Soup(x, "html.parser").text
)


def get_relative_links(url: str) -> list[str]:
    response = make_request(url)
    if response.status_code != 200:
        logger.error(f"Failed to download {url}. Status code: {response.status_code}")
        return []
    
    soup = parse_html(response.text)
    base_url = get_base_url(soup)
    
    urls = []
    links = soup.find_all("a", href=True)
    for link in links:
        href = link.get("href")
        if href:
            urls.append(urljoin(base_url, href))
    return urls

response = make_request(url)
if response.status_code != 200:
    logger.error(f"Failed to download {url}. Status code: {response.status_code}")

soup = parse_html(response.text)

base_url = get_base_url(soup)

urls = []
links = soup.find_all("a", class_="sfgov-topic-card")
for link in links:
    href = link.get("href")
    if href:
        urls.append(urljoin(base_url, href))   
        
model_id = "meta-llama/Meta-Llama-3-8B"