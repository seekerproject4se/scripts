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

        # --- BASIC EMAIL AND PHONE EXTRACTION (general, not format-specific) ---
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'
        emails_from_text = re.findall(email_pattern, data['RawText'])
        phones_from_text = re.findall(phone_pattern, data['RawText'])
        data['Emails'].extend([e for e in emails_from_text if e not in data['Emails']])
        data['PhoneNumbers'].extend([p for p in phones_from_text if p not in data['PhoneNumbers']])

        # --- DYNAMIC DONOR PROFILE EXTRACTION (robust, positive-signal only) ---
        def is_valid_email(email):
            # Accept any valid email
            return bool(email)
        def is_valid_phone(phone):
            digits = re.sub(r'\D', '', phone)
            # Require at least 10 digits, not a year, not a price
            if len(digits) < 10:
                return False
            if re.fullmatch(r'\d{4}', phone):
                return False
            if re.match(r'\$?\d+[\.,]?\d*', phone):
                return False
            return True
        def is_plausible_name(name):
            # At least two words, not all upper/lower, no numbers/special chars (except hyphen, apostrophe)
            if not name or len(name) < 2:
                return False
            # Allow single-word names if they are capitalized and not a common word
            if len(name.split()) == 1:
                if not name[0].isupper():
                    return False
                if name.lower() in ['contact', 'email', 'phone', 'info', 'support', 'home', 'about', 'learn', 'events', 'application', 'portal', 'president', 'vice', 'director', 'manager', 'grantmaking', 'carolina', 'theatre', 'community', 'grant', 'donor', 'profile', 'team', 'staff', 'fund', 'advisor', 'services', 'resources', 'grant', 'scholarships', 'mutual', 'fund', 'shares', 'investment', 'management', 'reporting', 'general', 'inquiries', 'media', 'requests', 'volunteer']:
                    return False
            # Not all upper/lower, no numbers/special chars (except hyphen, apostrophe)
            if name.isupper() or name.islower():
                return False
            if re.search(r'[^a-zA-Z\s\-\']', name):
                return False
            return True
        seen_profiles = set()
        for block in soup.find_all(['tr', 'li', 'div', 'section']):
            block_text = block.get_text(separator=' ', strip=True)
            if len(block_text) < 15 or len(block_text) > 400:
                continue
            email_match = re.search(email_pattern, block_text)
            phone_match = re.search(phone_pattern, block_text)
            # Improved name extraction: allow single word, all caps, and fallback to nearby text
            name_match = re.search(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*|[A-Z]{2,}(?: [A-Z]{2,})*)', block_text)
            name = name_match.group().strip() if name_match else ''
            # Fallback: if no name, try previous sibling or heading
            if not name:
                prev = block.find_previous(['h1', 'h2', 'h3', 'h4', 'b', 'strong'])
                if prev:
                    prev_text = prev.get_text(separator=' ', strip=True)
                    prev_name_match = re.search(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*|[A-Z]{2,}(?: [A-Z]{2,})*)', prev_text)
                    name = prev_name_match.group().strip() if prev_name_match else ''
            email = email_match.group() if email_match else None
            phone = phone_match.group() if phone_match else None
            if not ((email and is_valid_email(email)) or (phone and is_valid_phone(phone))):
                continue
            if not is_plausible_name(name):
                # Fallback: use first 2-3 words before email/phone as name if they look like a name
                if email:
                    before_email = block_text.split(email)[0].strip()
                    possible_name = ' '.join(before_email.split()[-3:])
                    if is_plausible_name(possible_name):
                        name = possible_name
                elif phone:
                    before_phone = block_text.split(phone)[0].strip()
                    possible_name = ' '.join(before_phone.split()[-3:])
                    if is_plausible_name(possible_name):
                        name = possible_name
            if not is_plausible_name(name):
                continue
            profile_key = (name.lower(), email or '', phone or '')
            if profile_key in seen_profiles:
                continue
            seen_profiles.add(profile_key)
            profile = {
                'name': name,
                'emails': [email] if email else [],
                'phone_numbers': [phone] if phone else [],
                'donations': [],
                'source': url,
                'context': block_text
            }
            data['Profiles'].append(profile)

        logging.info(f"Data extraction complete for URL: {url}")
        return data