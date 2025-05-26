import argparse
import logging
from flask import Flask
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from parsers import HTMLParser, DataManager, CSVExporter, ContactParser
from utils import get_sanitized_url_directory, save_html_content, fetch_html, run_puppeteer_script
from routes import setup_routes

app = Flask(__name__)

logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

session = HTMLSession()

class Parser:
    def __init__(self):
        self.data_manager = DataManager()
        self.processed_urls = set()  # Use a set for processed_urls

    def fetch_sitemap(self, url):
        sitemap_url = urljoin(url, "/sitemap.xml")
        response = fetch_html(sitemap_url)
        if not response:
            logging.error(f"Failed to fetch sitemap for {url}")
            return []
        soup = BeautifulSoup(response, "xml")
        urls = [loc.text for loc in soup.find_all("loc")]
        logging.info(f"Discovered {len(urls)} URLs from sitemap: {sitemap_url}")
        return urls

    def filter_urls(self, urls, keywords):
        filtered_urls = [url for url in urls if any(keyword in url for keyword in keywords)]
        logging.info(f"Filtered URLs: {filtered_urls}")
        return filtered_urls

    def parse_data(self, url):
        if url in self.processed_urls:
            logging.info(f"Skipping already processed URL: {url}")
            return
        if url not in self.processed_urls:
            self.processed_urls.add(url)
        html = fetch_html(url)
        if not html:
            logging.error(f"Skipping URL due to failed HTML fetch: {url}")
            return
        save_html_content(html, url)
        
        # Extract data using HTMLParser
        extracted_data = HTMLParser.extract_data_from_html(html, url)
        
        # Update data manager with extracted data
        self.data_manager.update_data(extracted_data)
        
        # Run Puppeteer script for additional data
        puppeteer_data = run_puppeteer_script(url)
        if puppeteer_data:
            self.data_manager.update_data(puppeteer_data)
        
        # Save results
        domain_directory = get_sanitized_url_directory(url)
        self.data_manager.save_to_file(domain_directory)

    def save_csv(self, url):
        CSVExporter.save_csv(self.data_manager.card_dict, url)

    def crawl_site(self, start_url, max_depth=2, keywords=None):
        """
        Recursively crawl the website starting from start_url, up to max_depth.
        Only follow internal links.
        """
        to_visit = [(start_url, 0)]
        visited = []
        domain = urlparse(start_url).netloc

        while to_visit:
            current_url, depth = to_visit.pop(0)
            if current_url in visited or depth > max_depth:
                continue
            if current_url not in visited:
                visited.append(current_url)
            logging.info(f"Crawling {current_url} at depth {depth}")
            html = fetch_html(current_url)
            if not html:
                continue
            # Extract data from this page
            HTMLParser.extract_data_from_html(html, current_url, self.data_manager.card_dict)
            # Optionally run Puppeteer
            puppeteer_data = run_puppeteer_script(current_url)
            if puppeteer_data:
                self.data_manager.update_data(puppeteer_data)
            # Find internal links
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                abs_url = urljoin(current_url, href)
                parsed = urlparse(abs_url)
                if parsed.netloc == domain and abs_url not in visited:
                    if keywords is None or any(kw in abs_url for kw in keywords):
                        to_visit.append((abs_url, depth + 1))
        # Save results
        domain_directory = get_sanitized_url_directory(start_url)
        self.data_manager.save_to_file(domain_directory)
        self.save_csv(start_url)
        logging.info("Crawling complete.")

if __name__ == '__main__':
    parser_arg = argparse.ArgumentParser(description='Run the Flask app or scan a website.')
    parser_arg.add_argument('--mode', choices=['runserver', 'scan'], default='runserver', help='Mode: runserver or scan')
    parser_arg.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the app on.')
    parser_arg.add_argument('--port', type=int, default=5001, help='Port to run the app on.')
    parser_arg.add_argument('--url', type=str, help='Target URL for scanning')
    parser_arg.add_argument('--max-depth', type=int, default=2, help='Max crawl depth')
    parser_arg.add_argument('--keywords', nargs='*', help='Optional keywords to filter URLs')
    args = parser_arg.parse_args()

    if args.mode == 'runserver':
        setup_routes(app)
        # Example: Using ContactParser to fetch Gmail contacts
        contact_parser = ContactParser()
        gmail_contacts = contact_parser.fetch_contacts(
            system='google',
            credentials_file='credentials.json'
        )
        contact_parser.save_to_csv("gmail_contacts.csv")
        app.run(host=args.host, port=args.port)
    elif args.mode == 'scan':
        if not args.url:
            print("Please provide a --url to scan.")
            exit(1)
        parser = Parser()
        parser.crawl_site(
            start_url=args.url,
            max_depth=args.max_depth,
            keywords=args.keywords
        )
        print("Scan complete. Data saved.")
