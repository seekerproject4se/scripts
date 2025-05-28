import re
from datetime import datetime

class DonorProfile:
    def __init__(self, name=None, source_url=None):
        self.name = name
        self.source_url = source_url
        self.emails = []  # Changed from set to list
        self.phone_numbers = []  # Changed from set to list
        self.addresses = []  # Changed from set to list
        self.donations = []
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.metadata = {
            'organization': None,
            'campaigns': [],  # Changed from set to list
            'donation_types': [],  # Changed from set to list
            'pdf_sources': [],  # Changed from set to list
            'email_sources': [],  # Added for consistency
            'phone_sources': [],  # Added for consistency
            'address_sources': []  # Added for consistency
        }

    def add_email(self, email, source=None):
        if self._validate_email(email):
            if email not in self.emails:
                self.emails.append(email)
            if source and source not in self.metadata['email_sources']:
                self.metadata['email_sources'].append(source)
            self.last_seen = datetime.now()

    def add_phone(self, phone, source=None):
        if self._validate_phone(phone):
            if phone not in self.phone_numbers:
                self.phone_numbers.append(phone)
            if source and source not in self.metadata['phone_sources']:
                self.metadata['phone_sources'].append(source)
            self.last_seen = datetime.now()

    def add_address(self, address, source=None):
        if self._validate_address(address):
            if address not in self.addresses:
                self.addresses.append(address)
            if source and source not in self.metadata['address_sources']:
                self.metadata['address_sources'].append(source)
            self.last_seen = datetime.now()

    def add_donation(self, amount, source=None, context=None, date=None):
        donation = {
            'amount': amount,
            'source': source,
            'context': context,
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'type': self._determine_donation_type(context)
        }
        if donation not in self.donations:
            self.donations.append(donation)
        self.last_seen = datetime.now()

    def _validate_email(self, email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _validate_phone(self, phone):
        pattern = r'\+?[1-9]\d{1,2}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        return bool(re.match(pattern, phone))

    def _validate_address(self, address):
        pattern = r'\d{1,5}\s\w+(\s\w+)*,\s\w+(\s\w+)*,\s[A-Z]{2}\s\d{5}'
        return bool(re.match(pattern, address))

    def _determine_donation_type(self, context):
        if not context:
            return 'unknown'
        
        context = context.lower()
        if any(word in context for word in ['monthly', 'recurring', 'regular']):
            return 'recurring'
        if any(word in context for word in ['one-time', 'single', 'special']):
            return 'one-time'
        if any(word in context for word in ['pledge', 'promise', 'commitment']):
            return 'pledge'
        return 'unknown'

    def to_dict(self):
        return {
            'name': self.name,
            'source_url': self.source_url,
            'emails': self.emails,  # Already a list
            'phone_numbers': self.phone_numbers,  # Already a list
            'addresses': self.addresses,  # Already a list
            'donations': self.donations,
            'metadata': self.metadata,
            'first_seen': self.first_seen.strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': self.last_seen.strftime('%Y-%m-%d %H:%M:%S')
        }
