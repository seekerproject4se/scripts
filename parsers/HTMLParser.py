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
        phone_pattern = r'(?:\\+?\\d{1,2}[\\s.-]?)?(?:\\(?\\d{3}\\)?[\\s.-]?)?\\d{3}[\\s.-]?\\d{4}'
        emails_from_text = re.findall(email_pattern, data['RawText'])
        phones_from_text = re.findall(phone_pattern, data['RawText'])
        # Add to data, deduplicating
        data['Emails'].extend([e for e in emails_from_text if e not in data['Emails']])
        data['PhoneNumbers'].extend([p for p in phones_from_text if p not in data['PhoneNumbers']])

        # Donor-related keywords
        donor_keywords = [
            'donor', 'contributor', 'supporter', 'member', 'user', 'profile',
            'first name', 'last name', 'email', 'address', 'donation', 'contribution',
            'amount', 'gift', 'pledge', 'donor list', 'donor information',
            'donor profile', 'donor page'
        ]

        # Function to check if text is likely a name
        def is_likely_name(text):
            words = text.split()
            return (2 <= len(words) <= 3 and 
                    all(word.isalpha() and word[0].isupper() for word in words))

        # Create donor profiles
        donor_profiles = []
        emails = []
        phones = []
        donations = []
        addresses = []
        
        # Extract data from structured elements
        for section in soup.find_all(['div', 'section', 'form', 'table']):
            text = section.get_text(strip=True).lower()
            if any(keyword in text for keyword in donor_keywords):
                # Extract form data
                profile = {
                    'name': '',
                    'first_name': '',
                    'last_name': '',
                    'emails': [],
                    'phone_numbers': [],
                    'addresses': [],
                    'donations': [],
                    'source': url,
                    'context': section.get_text(strip=True),
                    'first_seen': datetime.now().isoformat(),
                    'last_seen': datetime.now().isoformat()
                }

                # Extract form inputs
                for input in section.find_all('input', {'name': True}):
                    name = input.get('name', '').lower()
                    value = input.get('value', '')
                    if value and value.strip():
                        if 'email' in name:
                            profile['emails'].append(value)
                            emails.append(value)
                        elif 'phone' in name:
                            phone_number = re.sub(r'[^\d]', '', value)
                            if len(phone_number) >= 10:
                                profile['phone_numbers'].append(phone_number)
                                phones.append(phone_number)
                        elif 'first_name' in name:
                            profile['first_name'] = value
                        elif 'last_name' in name:
                            profile['last_name'] = value
                        elif 'address' in name:
                            profile['addresses'].append(value)
                            addresses.append(value)

                # Extract donation amounts
                donation_pattern = r'\$?\d+(?:,\d{3})*(?:\.\d{2})?'
                for amount in re.finditer(donation_pattern, section.get_text()):
                    context = section.get_text()[max(0, amount.start()-50):amount.end()+50]
                    if any(keyword in context.lower() for keyword in donor_keywords):
                        donation = {
                            'amount': amount.group(),
                            'source': url,
                            'context': context
                        }
                        profile['donations'].append(donation)
                        donations.append(donation)  # Append to list instead of set

                # Combine first and last name if both exist
                if profile['first_name'] and profile['last_name']:
                    profile['name'] = f"{profile['first_name']} {profile['last_name']}"
                elif profile['first_name'] or profile['last_name']:
                    profile['name'] = profile['first_name'] or profile['last_name']

                if profile['name'] or profile['emails'] or profile['phone_numbers']:
                    donor_profiles.append(profile)

        # Add data to the dictionary
        data['Profiles'].extend(donor_profiles)
        data['Emails'].extend(emails)
        data['PhoneNumbers'].extend(phones)
        data['Donations'].extend(donations)
        data['Addresses'].extend(addresses)
        data['Names'].extend(names)
        
        # Convert any sets to lists in the donor profiles
        for profile in data['Profiles']:
            for key, value in profile.items():
                if isinstance(value, set):
                    profile[key] = list(value)
        
        # Convert any sets to lists in the donations
        for donation in data['Donations']:
            for key, value in donation.items():
                if isinstance(value, set):
                    donation[key] = list(value)

        # Extract PDF links
        pdf_links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if href.endswith('.pdf') and any(keyword in href for keyword in donor_keywords):
                full_url = urljoin(url, href)
                if full_url not in pdf_links:
                    pdf_links.append(full_url)
        data['PDFLinks'] = pdf_links

        # Remove duplicates while preserving order
        data['Emails'] = list(dict.fromkeys(data['Emails']))
        data['PhoneNumbers'] = list(dict.fromkeys(data['PhoneNumbers']))
        data['Names'] = list(dict.fromkeys(data['Names']))
        data['Addresses'] = list(dict.fromkeys(data['Addresses']))
        
        # For donations, we need to handle duplicates differently since they're dictionaries
        seen_donations = set()
        unique_donations = []
        for donation in data['Donations']:
            donation_key = f"{donation.get('amount', '')}_{donation.get('source', '')}"
            if donation_key not in seen_donations:
                seen_donations.add(donation_key)
                unique_donations.append(donation)
        data['Donations'] = unique_donations

        # Log final data counts
        logging.info(f"Final data counts:")
        logging.info(f"  Donor Profiles: {len(data['Profiles'])}")
        logging.info(f"  Emails: {len(data['Emails'])}")
        logging.info(f"  Phone Numbers: {len(data['PhoneNumbers'])}")
        logging.info(f"  Addresses: {len(data['Addresses'])}")
        logging.info(f"  Donations: {len(data['Donations'])}")
        logging.info(f"  PDF Links: {len(data['PDFLinks'])}")
        return data

    def __init__(self):
        self.processed_urls = set()  # Use a set for processed_urls