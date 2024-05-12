""" Processes a list of visited URLs and identifies external URLs that are redirects.

The main functionality is provided by the script itself, which:
1. Reads a list of visited URLs from a JSON file named "data/visited_urls_edited.json".
2. For each URL in the list, it checks if the URL is valid using the `is_url_valid()` 
    function from the `smart_scraper` module.
3. If the URL is valid and is a redirect (determined using the `is_url_redirect()` 
    function from the `smart_scraper` module), the redirect URL is added to the 
    `external_urls` dictionary.
4. If the URL is not valid, the script attempts to remove the topic from the URL 
    (using the `remove_topic_from_url()` function) and checks if the resulting URL 
    is valid.
5. If the URL without the topic is valid, it replaces the original URL in the 
    `visited_urls` dictionary.
6. If the URL without the topic is a redirect, the redirect URL is added to the 
    `external_urls` dictionary.

The module uses the `requests` library to check if a URL is a redirect and to get 
the redirect URL.

The `remove_topic_from_url()` function is a utility function that removes the topic 
from a URL. It replaces "sf.gov/topics/" with "sf.gov/" in the URL.

The script relies on the `is_url_valid()` and `is_url_redirect()` functions from the 
`smart_scraper` module to check the validity and redirect status of URLs.

To use this module, ensure that the required dependencies are installed and that the 
"data/visited_urls_edited.json" file exists with the list of visited URLs. 
The script will process the URLs and update the `visited_urls` dictionary with valid 
URLs and add redirect URLs to the `external_urls` dictionary.
"""

import json
import requests

from loguru import logger
from smart_scraper import is_url_valid, is_url_redirect


def remove_topic_from_url(url: str) -> str:
    """Remove the topic from a URL.

    Args:
        url: The URL to remove the topic from.

    Returns:
        The URL with the topic removed.
    """
    return url.replace("sf.gov/topics/", "sf.gov/")


with open("data/visited_urls_edited.json", "r") as f:
    visited_urls = json.load(f)

external_urls = {}

url_count = len(visited_urls)
for i, url in enumerate(visited_urls):
    logger.info(f"{i}/{url_count}: Checking {url}")
    if is_url_valid(url):
        if is_url_redirect(url):
            redirected_url = requests.head(url, allow_redirects=True, verify=False).url
            external_urls[redirected_url] = ""
    else:
        possible_url = remove_topic_from_url(url)
        if is_url_valid(possible_url):
            visited_urls[possible_url] = visited_urls.pop(url)
            if is_url_redirect(possible_url):
                redirected_url = requests.head(
                    possible_url, allow_redirects=True, verify=False
                ).url
                external_urls[redirected_url] = ""
