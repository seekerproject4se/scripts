import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from utils import save_html_content, fetch_html
from config import TOR_PROXY, key_data_patterns

class HTMLParser:
    @staticmethod
    def parse_html(url, processed_urls):
        """
        Parses the HTML content of a given URL, avoiding duplicates.

        Args:
            url (str): The URL to parse.
            processed_urls (set): A set of already processed URLs.

        Returns:
            str: The raw HTML content, or None if the URL was already processed.
        """
        if url in processed_urls:
            logging.info(f"Skipping already processed URL: {url}")
            return None

        html_content = fetch_html(url, proxy=TOR_PROXY)  # Use TOR_PROXY if needed
        if html_content is None:
            logging.error(f"Failed to fetch HTML for {url}")
            return None

        processed_urls.add(url)
        return html_content

    @staticmethod
    def extract_data_from_html(html, url):
        """
        Extract relevant data (donor/user information) from the HTML content.
        
        Returns:
            dict: A dictionary containing extracted data with proper data structures
        """
        logging.info(f"Starting HTML parsing for URL: {url}")
        soup = BeautifulSoup(html, 'html.parser')

        # Initialize data structures with lists for consistency
        data = {
            'Profiles': [],
            'Emails': [],
            'PhoneNumbers': [],
            'Donations': [],
            'PDFLinks': [],
            'RawText': '',
            'Names': [],
            'Addresses': [],
            'Entities': [],
            'Donors': []
        }

        # Ensure all extracted data is initialized as lists
        emails = []
        phones = []
        donations = []
        addresses = []
        names = []
        donor_profiles = []

        # Extract all visible text
        data['RawText'] = soup.get_text(' ', strip=True)

        # --- NEW: Extract emails and phone numbers from the full text ---
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'
        # FIX: Use correct regex (single backslashes in a raw string)
        phone_pattern = r'(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'
        # CORRECT: Use a single, clean definition (no repetition)
        phone_pattern = r'(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'
        emails_from_text = re.findall(email_pattern, data['RawText'])
        phones_from_text = re.findall(phone_pattern, data['RawText'])
        # Add to data, deduplicating
        data['Emails'].extend([e for e in emails_from_text if e not in data['Emails']])
        data['PhoneNumbers'].extend([p for p in phones_from_text if p not in data['PhoneNumbers']])

        # --- EXISTING CODE FOR DATA EXTRACTION ---
        # Extract email addresses
        emails = soup.find_all(string=re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'))
        data['Emails'] = list(set(data['Emails'] + [email.strip() for email in emails]))

        # Extract phone numbers
        phones = soup.find_all(string=re.compile(r'(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'))
        data['PhoneNumbers'] = list(set(data['PhoneNumbers'] + [phone.strip() for phone in phones]))

        # Extract donation information based on common patterns
        for pattern in key_data_patterns['donation']:
            for match in re.finditer(pattern, data['RawText']):
                donations.append(match.group())
        data['Donations'] = list(set(data['Donations'] + donations))

        # Extract names (assuming they are in 'h1', 'h2', or 'h3' tags for prominence)
        name_tags = soup.find_all(['h1', 'h2', 'h3'])
        for tag in name_tags:
            if tag.get_text(strip=True) not in data['Names']:
                data['Names'].append(tag.get_text(strip=True))

        # Extract addresses (naive approach, can be improved with more context)
        address_pattern = re.compile(r'\d{1,5}\s\w+(\s\w+){1,3},?\s\w+,\s?\w{2,}?\s?\d{5}(-\d{4})?')
        addresses = soup.find_all(string=address_pattern)
        data['Addresses'] = list(set(data['Addresses'] + [address.strip() for address in addresses]))

        # --- NEW: Extract donor profiles and entities ---
        # Assuming donor profiles are linked in a specific section, e.g., "Our Donors"
        donor_section = soup.find(id='our-donors')
        if donor_section:
            donor_links = donor_section.find_all('a', href=True)
            for link in donor_links:
                profile_url = urljoin(url, link['href'])
                if profile_url not in data['Profiles']:
                    data['Profiles'].append(profile_url)

        # Entities extraction (assuming they are mentioned in a specific format)
        entity_pattern = re.compile(r'\b(?:Foundation|Inc|LLC|Group|Trust)\b', re.IGNORECASE)
        entities = soup.find_all(string=entity_pattern)
        data['Entities'] = list(set(data['Entities'] + [entity.strip() for entity in entities]))

        # --- NEW: Extract donor names specifically ---
        # Assuming donor names are in a specific section or format
        donor_name_tags = soup.find_all(['h4', 'h5', 'p'], string=re.compile(r'Donor:'))
        for tag in donor_name_tags:
            donor_name = tag.get_text(strip=True).replace('Donor:', '').strip()
            if donor_name and donor_name not in data['Donors']:
                data['Donors'].append(donor_name)

        logging.info(f"Data extraction complete for URL: {url}")
        return data