import imaplib
import email
from email.header import decode_header
from urllib.parse import urlparse
import os
import csv
import re
import logging
from datetime import datetime
from parsers.DonorProfile import DonorProfile

class EmailExtractor:
    """
    A robust parser to extract email contact information (email address, name, physical address, phone number)
    and save it to a CSV file. It avoids duplicating data so that it can be used to extract only new entries.
    """

    # Define email file extensions
    EMAIL_FILE_EXTENSIONS = ['.eml', '.mbox']

    def __init__(self, host=None, username=None, password=None):
        self.host = host
        self.username = username
        self.password = password
        self.mail = None  # Initialize the IMAP connection as None
                
        # Initialize data structure with lists
        self.contact_data = {
            'emails': [],
            'phone_numbers': [],
            'addresses': [],
            'profiles': []
        }
        self.processed_emails = set()  # Use a set for processed_emails

    @staticmethod
    def extract_contact_info(self, text, source):
        """
        Extracts contact information (email, name, address, phone) from the given text.

        Args:
            text (str): The text content to extract contact information from.
            source (str): The source of the contact information

        Returns:
            dict: A dictionary containing the extracted contact information.
        """
        # Extract email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,7}'
        emails = re.findall(email_pattern, text)
        
        # Extract names (basic heuristic for names)
        name_pattern = r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b'  # Matches "First Last"
        names = re.findall(name_pattern, text)
        
        # Extract physical addresses
        address_pattern = r'\d{1,5}\s\w+(\s\w+)*,\s\w+,\s[A-Z]{2}\s\d{5}'  # Matches "123 Main St, City, ST 12345"
        addresses = re.findall(address_pattern, text)
        
        # Extract phone numbers (use a robust, consistent pattern)
        phone_pattern = r'(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'  # Matches international and US phone numbers
        phones = re.findall(phone_pattern, text)
        
        # Only create profile if we have valid information
        if emails or names or addresses or phones:
            donor_profile = DonorProfile(name=names[0] if names else None, source_url=source)
            for email in emails:
                donor_profile.add_email(email, source='email')
            for phone in phones:
                donor_profile.add_phone(phone, source='email')
            for address in addresses:
                donor_profile.add_address(address, source='email')
            profile_dict = donor_profile.to_dict()
            # Update our data structure
            self.contact_data['profiles'].append(profile_dict)
            # Update individual collections
            for email in donor_profile.emails:
                if email not in self.contact_data['emails']:
                    self.contact_data['emails'].append(email)
            for phone in donor_profile.phone_numbers:
                if phone not in self.contact_data['phone_numbers']:
                    self.contact_data['phone_numbers'].append(phone)
            for address in donor_profile.addresses:
                if address not in self.contact_data['addresses']:
                    self.contact_data['addresses'].append(address)
            return profile_dict
        return None

    def connect_to_email(self):
        """
        Connects to the email server using the provided host, username, and password.
        """
        try:
            if not self.host or not self.username or not self.password:
                raise ValueError("Email server credentials are not provided.")
            self.mail = imaplib.IMAP4_SSL(self.host)
            self.mail.login(self.username, self.password)
            logging.info("Connected to email server successfully.")
        except Exception as e:
            logging.error(f"Error connecting to email server: {e}")
            raise

    def parse_emails(self, folder='INBOX'):
        """
        Parses emails from the specified folder (default is 'INBOX') and extracts contact information.

        Args:
            folder (str): The folder to parse emails from.
        """
        try:
            if not self.mail:
                raise ValueError("IMAP connection is not established. Call connect_to_email() first.")
            self.mail.select(folder)
            _, data = self.mail.search(None, 'ALL')
            for num in data[0].split():
                _, data = self.mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                email_message = email.message_from_bytes(raw_email)

                # Extract email body
                body = None
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
                    elif content_type == "text/html" and body is None:
                        body = part.get_payload(decode=True).decode()

                if body:
                    # Extract contact info and update our data structure
                    profile = self.extract_contact_info(body, f"email_{num}")
                    if profile:
                        logging.info(f"Extracted contact info from email {num}")

                if body:
                    # Extract contact information from the email body
                    contact_info = self.extract_contact_info(body)

                    # Check if the email has already been processed
                    email_id = contact_info['Email']
                    if email_id and email_id not in self.processed_emails:
                        self.processed_emails.add(email_id)
                        self.contact_data.append(contact_info)
            logging.info(f"Parsed {len(self.contact_data)} contacts from folder '{folder}'.")
        except Exception as e:
            logging.error(f"Error parsing emails from folder '{folder}': {e}")

    def parse_email_files(self, directory):
        """
        Parses email files (e.g., .eml, .mbox) in a directory and extracts contact information.

        Args:
            directory (str): The directory containing email files.
        """
        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    _, file_extension = os.path.splitext(file_path)
                    if file_extension in self.EMAIL_FILE_EXTENSIONS:
                        logging.info(f"Processing email file: {file_path}")
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            contact_info = self.extract_contact_info(content)
                            email_id = contact_info['Email']
                            if email_id and email_id not in self.processed_emails:
                                self.processed_emails.add(email_id)
                                self.contact_data.append(contact_info)
        except Exception as e:
            logging.error(f"Error parsing email files in directory '{directory}': {e}")

    def save_to_csv(self, url):
        """
        Saves the extracted contact information to a CSV file named after the URL of the site being scraped.

        Args:
            url (str): The URL of the site being scraped.
        """
        try:
            parsed_url = urlparse(url)
            filename = f"{parsed_url.netloc.replace('.', '_')}_contacts.csv"

            # Define the fieldnames for the CSV file
            fieldnames = ['Email', 'Name', 'Address', 'Phone']

            # Write to CSV
            if not os.path.exists(filename):
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
            with open(filename, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                for contact in self.contact_data:
                    writer.writerow(contact)
            self.contact_data = []
            logging.info(f"Saved contact information to CSV file: {filename}")
        except Exception as e:
            logging.error(f"Error saving contact information to CSV: {e}")