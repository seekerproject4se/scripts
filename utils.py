import os
import logging
import json
import time
import subprocess
from datetime import datetime
from urllib.parse import urlparse
import requests
from config import TOR_PROXY  # Import TOR_PROXY from config.py


def sanitize_url(url):
    """
    Sanitizes a URL by replacing dots in the domain with underscores and removing query parameters/fragments.

    Args:
        url (str): The URL to sanitize.

    Returns:
        str: The sanitized URL.
    """
    parsed_url = urlparse(url)
    sanitized = parsed_url.netloc.replace('.', '_')  # Replace dots with underscores
    return sanitized


def get_sanitized_url_directory(url):
    """
    Creates and returns a sanitized directory path for the domain of the given URL.

    Args:
        url (str): The URL to create a directory for.

    Returns:
        str: The path to the sanitized directory.
    """
    domain = sanitize_url(url)
    directory = f"data/{domain}"
    os.makedirs(directory, exist_ok=True)  # Ensure the directory exists
    return directory


def save_html_content(html, url):
    """
    Saves the raw HTML content to a file for debugging purposes.

    Args:
        html (str): The raw HTML content.
        url (str): The URL of the page.

    Returns:
        str: The path to the saved HTML file.
    """
    directory = get_sanitized_url_directory(url)  # Use the sanitized directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_path = os.path.join(directory, f'raw_html_{timestamp}.html')
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(html)
        logging.info(f"HTML content saved to: {file_path}")
    except OSError as e:
        logging.error(f"Error saving HTML content to {file_path}: {e}")
        raise
    return file_path


def make_request(url, headers=None, proxies=None, max_retries=3, backoff_factor=1):
    """
    Makes an HTTP request with retries and exponential backoff.

    Args:
        url (str): The URL to request.
        headers (dict): Optional headers for the request.
        proxies (dict): Optional proxies for the request.
        max_retries (int): Maximum number of retries.
        backoff_factor (int): Backoff factor for retries.

    Returns:
        requests.Response: The HTTP response object, or None if the request fails.
    """
    retries = 0
    while retries < max_retries:
        try:
            logging.info(f"Attempting request to {url} (Attempt {retries + 1}/{max_retries})")
            response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
            response.raise_for_status()
            logging.info(f"Request successful for {url}")
            return response
        except requests.exceptions.RequestException as e:
            retries += 1
            logging.warning(f"Request failed: {e}. Retrying {retries}/{max_retries}...")
            time.sleep(backoff_factor * (2 ** (retries - 1)))
    logging.error(f"Failed to fetch {url} after {max_retries} retries.")
    return None


def fetch_html(url):
    """
    Fetches the HTML content of a given URL.

    Args:
        url (str): The URL to fetch.

    Returns:
        str: The HTML content of the page, or None if the request fails.
    """
    logging.info(f"Fetching HTML for URL: {url}")
    response = make_request(url, headers={}, proxies=TOR_PROXY, max_retries=5, backoff_factor=1)
    if response is None:
        response = make_request(url, headers={}, proxies=None, max_retries=5, backoff_factor=1)
    if response is None:
        logging.error(f"Failed to fetch HTML for {url}")
        return None
    return response.text


def run_puppeteer_script(url):
    """
    Run Puppeteer script to extract data from the given URL.

    Args:
        url (str): The URL to process.

    Returns:
        dict: The extracted data from Puppeteer, or None if the script fails.
    """
    try:
        result = subprocess.run(['node', 'search_puppeteer.js', url], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Puppeteer script ran successfully for {url}")
            return json.loads(result.stdout)
        else:
            logging.error(f"Puppeteer script failed for {url} with error: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error running Puppeteer script for {url}: {e}")
        return None