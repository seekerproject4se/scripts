# parser class modulized
import argparse
import logging
import os
import re
import time
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urljoin
from flask import Flask, request, jsonify
from requests_html import HTMLSession
import fitz  # PyMuPDF
import hashlib
import json
from bs4 import BeautifulSoup
import requests
from parsers import EmailExtractor, PDFExtractor, FileDownloader, HTMLParser, CSVExporter, DataManager
from utils import get_sanitized_url_directory
from config import TOR_PROXY  # Import TOR_PROXY from config.py

app = Flask(__name__)

# Set up logging with timestamps
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

# Email file extensions
EMAIL_FILE_EXTENSIONS = ['.eml', '.mbox']
PDF_FILE_EXTENSION = '.pdf'

session = HTMLSession()

def sanitize_url(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc.replace('.', '_')  # Use '_' instead of '.' for directory names

def get_sanitized_url_directory(url):
    """
    Return a directory path based on the domain of the URL.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('.', '_')  # Use the domain name for the directory
    directory = f"data/{domain}"
    os.makedirs(directory, exist_ok=True)  # Ensure the directory exists
    return directory

def run_puppeteer_script(url):
    try:
        result = subprocess.run(['node', 'search_puppeteer.js', url], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Puppeteer script ran successfully for {url}")
            domain_directory = get_sanitized_url_directory(url)  # Use domain directory
            puppeteer_output = json.loads(result.stdout)

            # Save Puppeteer output to a single JSON file for the domain
            json_file_path = os.path.join(domain_directory, "puppeteer_data.json")
            if os.path.exists(json_file_path):
                with open(json_file_path, "r") as file:
                    existing_data = json.load(file)
            else:
                existing_data = {}

            # Merge new data with existing data
            for key, values in puppeteer_output.items():
                if key in existing_data:
                    existing_data[key] = list(set(existing_data[key] + values))
                else:
                    existing_data[key] = values

            with open(json_file_path, "w") as file:
                json.dump(existing_data, file, indent=4)

            return puppeteer_output
        else:
            logging.error(f"Puppeteer script failed for {url} with error: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error running Puppeteer script for {url}: {e}")
        return None

def make_request(url, headers, proxies, max_retries, backoff_factor):
    retries = 0
    while retries < max_retries:
        try:
            response = session.get(url, headers=headers, proxies=proxies, timeout=10)
            response.raise_for_status()
            logging.info(f"Received response from {url}")
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logging.error(f"Access forbidden (403) for {url}")
                break
            elif response.status_code == 429:  # Handle rate limiting
                retries += 1
                wait_time = backoff_factor * (2 ** (retries - 1))
                logging.error(f"Rate limited. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logging.error(f"HTTP error for {url}: {e}")
                break
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error for {url}: {e}")
            break
    return None

def fetch_html(url):
    response = make_request(url, headers={}, proxies=TOR_PROXY, max_retries=5, backoff_factor=1)
    if response is None:
        response = make_request(url, headers={}, proxies=None, max_retries=5, backoff_factor=1)
    if response is None:
        return None
    return response.text

def save_html_content(html, url, timestamp):
    """
    Saves the raw HTML content to a file for debugging purposes.
    """
    directory = get_sanitized_url_directory(url)
    file_path = os.path.join(directory, f'raw_html_{timestamp}.html')
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(html)

class Parser:
    def __init__(self):
        self.data_manager = DataManager()
        self.processed_urls = set()  # Track processed URLs

    def fetch_sitemap_urls(self, base_url):
        """
        Fetch and parse the sitemap.xml file to extract all URLs.

        Args:
            base_url (str): The base URL of the website.

        Returns:
            list: A list of URLs found in the sitemap.
        """
        sitemap_url = f"{base_url.rstrip('/')}/sitemap.xml"
        try:
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.text for loc in soup.find_all('loc')]

            # Filter URLs for relevance
            relevant_keywords = ['donate', 'contact', 'about', 'contribute', 'fund']
            filtered_urls = [url for url in urls if any(keyword in url.lower() for keyword in relevant_keywords)]
            logging.info(f"Filtered URLs: {filtered_urls}")
            return filtered_urls
        except Exception as e:
            logging.error(f"Failed to fetch sitemap from {sitemap_url}: {e}")
            return []

    def parse_data(self, url, timestamp):
        if url in self.processed_urls:
            logging.info(f"Skipping already processed URL: {url}")
            return
        self.processed_urls.add(url)
        logging.info(f"Processing URL: {url}")
        logging.info(f"Parsing data from {url}")

        # Fetch URLs from sitemap.xml
        sitemap_urls = self.fetch_sitemap_urls(url)
        if sitemap_urls:
            logging.info(f"Discovered {len(sitemap_urls)} URLs from sitemap.xml")
        else:
            logging.warning(f"No sitemap.xml found or no URLs discovered for {url}")
            sitemap_urls = [url]  # Fallback to the original URL if no sitemap is found

        # Process each URL from the sitemap
        for discovered_url in sitemap_urls:
            if discovered_url in self.processed_urls:
                logging.info(f"Skipping already processed URL: {discovered_url}")
                continue

            puppeteer_data = run_puppeteer_script(discovered_url)
            if puppeteer_data:
                logging.info(f"Puppeteer data extracted: {puppeteer_data}")
                self.data_manager.update_data(puppeteer_data)
                self.extract_from_pdfs(discovered_url)
            else:
                html = fetch_html(discovered_url)
                if not html:
                    logging.error(f"Failed to fetch HTML from {discovered_url}")
                    continue
                HTMLParser.extract_data_from_html(html, discovered_url, self.data_manager.card_dict)
                logging.info(f"Data after HTML parsing: {self.data_manager.card_dict}")

        # Save consolidated data to a single JSON file
        domain_directory = get_sanitized_url_directory(url)
        self.data_manager.save_to_file(domain_directory)
        logging.info(f"Finished processing {url}. Consolidated data saved.")

    def extract_from_pdfs(self, url):
        directory = get_sanitized_url_directory(url)
        for pdf_file in os.listdir(directory):
            if pdf_file.endswith(PDF_FILE_EXTENSION):
                file_path = os.path.join(directory, pdf_file)
                PDFExtractor.extract_from_pdf(file_path, self.data_manager.card_dict)

    def save_csv(self, url):
        CSVExporter.save_csv(self.data_manager.card_dict, url)

@app.route('/search', methods=['GET'])
def search():
    try:
        urls = request.args.getlist('urls')
        if not urls:
            return jsonify({"error": "No URLs provided"}), 400

        results = []
        parser = Parser()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for url in urls:
            if not is_valid_url(url):
                logging.error(f"Invalid URL: {url}")
                results.append({"url": url, "error": "Invalid URL"})
                continue

            try:
                parser.parse_data(url, timestamp)
                parser.save_csv(url)
                data_serializable = {
                    key: list(values) for key, values in parser.data_manager.card_dict.items()
                }
                results.append({
                    "url": url,
                    "data": data_serializable,
                    "summary": {
                        "emails_count": len(data_serializable['Emails']),
                        "names_count": len(data_serializable['Names']),
                        "addresses_count": len(data_serializable['Addresses']),
                        "pdf_links_count": len(data_serializable['PDFLinks']),
                    }
                })
            except Exception as e:
                logging.error(f"Error processing URL {url}: {e}")
                results.append({"url": url, "error": str(e)})

        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in search endpoint: {e}")
        return jsonify({"error": str(e)}), 500

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

if __name__ == '__main__':
    parser_arg = argparse.ArgumentParser(description='Run the Flask app.')
    parser_arg.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the app on.')
    parser_arg.add_argument('--port', type=int, default=5001, help='Port to run the app on.')
    args = parser_arg.parse_args()
    app.run(host=args.host, port=args.port)
