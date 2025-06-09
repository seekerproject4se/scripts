import logging
import re
from bs4 import BeautifulSoup
from utils import fetch_html, save_html_content, run_puppeteer_script, get_sanitized_url_directory
from parsers.DataManager import DataManager  # Import directly from the file
from parsers.CSVExporter import CSVExporter  # Import directly from the file
from parsers.HTMLParser import HTMLParser  # Import directly from the file



class Parser:
    def __init__(self):
        self.data_manager = DataManager()
        self.processed_urls = set()  # Use a set for processed_urls

    @staticmethod
    def is_valid_url(url):
        """
        Validate if the given URL is in a valid format.

        Args:
            url (str): The URL to validate.

        Returns:
            bool: True if the URL is valid, False otherwise.
        """
        url_pattern = re.compile(
            r'^(https?://)?'  # http:// or https://
            r'([a-zA-Z0-9.-]+)'  # domain name
            r'(\.[a-zA-Z]{2,})'  # top-level domain
            r'(:\d+)?'  # optional port
            r'(\/.*)?$'  # optional path
        )
        return re.match(url_pattern, url) is not None

    def fetch_sitemap(self, url):
        """
        Fetch and parse the sitemap of a URL.
        """
        sitemap_url = f"{url}/sitemap.xml"
        response = fetch_html(sitemap_url)
        if not response:
            logging.error(f"Failed to fetch sitemap for {url}")
            return []

        # Extract URLs from the sitemap
        soup = BeautifulSoup(response, "xml")
        urls = [loc.text for loc in soup.find_all("loc")]
        logging.info(f"Discovered {len(urls)} URLs from sitemap: {sitemap_url}")
        return urls

    def filter_urls(self, urls, keywords):
        """
        Filter URLs based on the presence of specific keywords.
        """
        filtered_urls = [url for url in urls if any(keyword in url for keyword in keywords)]
        logging.info(f"Filtered URLs: {filtered_urls}")
        return filtered_urls

    def parse_data(self, url):
        """
        Parse data from a URL, including HTML and PDFs.
        """
        if url in self.processed_urls:
            logging.info(f"Skipping already processed URL: {url}")
            return
        self.processed_urls.add(url)

        # Fetch HTML content
        html = fetch_html(url)
        if not html:
            logging.error(f"Skipping URL due to failed HTML fetch: {url}")
            return

        # Save raw HTML for debugging
        save_html_content(html, url)

        # Extract data from HTML
        html_data = HTMLParser.extract_data_from_html(html, url)
        if html_data:
            self.data_manager.update_data(html_data)

        # Run Puppeteer for additional data
        puppeteer_data = run_puppeteer_script(url)
        if puppeteer_data:
            self.data_manager.update_data(puppeteer_data)

        # Save consolidated data
        domain_directory = get_sanitized_url_directory(url)
        self.data_manager.save_to_file(domain_directory)

    def save_csv(self, url):
        """
        Save extracted data to a CSV file.
        """
        CSVExporter.save_csv(self.data_manager.card_dict, url)

    def crawl_site(self, start_url, max_depth=4, keywords=None):
        """
        Recursively crawl the site starting from start_url up to max_depth.
        Optionally filter URLs by keywords.
        """
        if keywords is None:
            keywords = []
        visited = set()

        def crawl(url, depth):
            if depth > max_depth or url in visited:
                return
            visited.add(url)
            self.parse_data(url)
            try:
                html = fetch_html(url)
                if not html:
                    return
                soup = BeautifulSoup(html, 'html.parser')
                for link in soup.find_all('a', href=True):
                    next_url = link['href']
                    # Normalize relative URLs
                    if not next_url.startswith('http'):
                        from urllib.parse import urljoin
                        next_url = urljoin(url, next_url)
                    # Filter by keywords if provided
                    if keywords and not any(kw.lower() in next_url.lower() for kw in keywords):
                        continue
                    if next_url not in visited:
                        crawl(next_url, depth + 1)
            except Exception as e:
                logging.error(f"Error crawling {url}: {e}")

        crawl(start_url, 1)