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
    def _is_plausible_donor_name(name):
        """
        Heuristic to determine if a string is a plausible donor name.
        - Not in navigation/menu/header keywords
        - At least two words
        - Not all uppercase or all lowercase
        - No numbers or special chars (except hyphen, apostrophe)
        - Not too short
        """
        if not name or len(name) < 5:
            return False
        nav_keywords = [
            'menu', 'about', 'contact', 'donate', 'give', 'events', 'news', 'search', 'login', 'privacy',
            'sitemap', 'newsletter', 'work with us', 'find us', 'careers', 'board', 'team', 'history',
            'resources', 'fees', 'forms', 'agreements', 'apply', 'scholarships', 'grants', 'support',
            'our affiliates', 'regional affiliates', 'foundation', 'center', 'gallery', 'conference',
            'directions', 'parking', 'media', 'publications', 'stories', 'insights', 'open a fund',
            'assets', 'investments', 'individuals', 'families', 'corporations', 'advisors', 'nonprofits',
            'helping you thrive', 'meeting space', 'explore', 'myfftc', 'directory', 'list', 'join', 'request space',
            'second nav', 'main nav', 'footer', 'header', 'home', 'find out', 'learn more', 'view all', 'connect with us',
            'philanthropyfocus.org', 'charlotte area community calendar', 'stage', 'set', 'playing', 'planned giving',
            'donor resources', 'fees', 'civic initiatives', 'support the robinson center', 'events & webinars',
            'luski-gorelick', 'belk place', 'carolina theatre', 'levine conference', 'luski gallery', 'robinson center',
            'north tryon', 'directory', 'email', 'directory', 'directory', 'email', 'directory', 'email', 'directory'
        ]
        name_lower = name.strip().lower()
        for kw in nav_keywords:
            if kw in name_lower:
                return False
        # At least two words
        if len(name.split()) < 2:
            return False
        # Not all uppercase or all lowercase
        if name.isupper() or name.islower():
            return False
        # No numbers or special chars (except hyphen, apostrophe)
        if re.search(r'[^a-zA-Z\s\-\']', name):
            return False
        return True

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
        pattern = key_data_patterns['donation']
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

        # --- DYNAMIC DONOR PROFILE EXTRACTION (signal-based) ---
        us_states = set([
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA',
            'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
            'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        ])
        zip_pattern = r'\b\d{5}(?:-\d{4})?\b'
        state_zip_pattern = re.compile(r'\b([A-Z]{2})\s+' + zip_pattern)
        for block in soup.find_all(['tr', 'li', 'div', 'section']):
            block_text = block.get_text(separator=' ', strip=True)
            email_match = re.search(email_pattern, block_text)
            phone_match = re.search(phone_pattern, block_text)
            donation_match = re.search(pattern, block_text)
            state_zip_match = state_zip_pattern.search(block_text)
            # Only treat as donor/contact profile if it contains an email, phone, or state+ZIP
            if email_match or phone_match or state_zip_match:
                # Try to extract a plausible name (two capitalized words, but not required)
                name_match = re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', block_text)
                name = name_match.group() if name_match else ''
                profile = {
                    'name': name,
                    'emails': [email_match.group()] if email_match else [],
                    'phone_numbers': [phone_match.group()] if phone_match else [],
                    'donations': [donation_match.group()] if donation_match else [],
                    'source': url,
                    'context': block_text
                }
                data['Profiles'].append(profile)

        logging.info(f"Data extraction complete for URL: {url}")
        return data