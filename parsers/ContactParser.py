from parsers.WordPressExtractor import WordPressExtractor
from parsers.GoogleExtractor import GoogleExtractor
from parsers.MicrosoftExtractor import MicrosoftExtractor
from .DataManager import DataManager
import logging
from datetime import datetime

class ContactParser:
    def __init__(self, data_manager=None):
        """
        Initialize ContactParser with optional DataManager instance.
        
        Args:
            data_manager (DataManager, optional): The DataManager instance to use. 
                If None, will create a new DataManager instance.
        """
        self.data_manager = data_manager or DataManager()
        self.contacts = self.data_manager.card_dict

    def fetch_contacts(self, system, **kwargs):
        """
        Fetches contacts from the specified system.

        Args:
            system (str): The system to fetch contacts from (e.g., 'wordpress', 'google', 'microsoft').
            kwargs: Additional arguments required for the specific system.

        Returns:
            dict: A dictionary containing contact information with proper data structures.
        """
        if system == 'wordpress':
            extractor = WordPressExtractor(kwargs['site_url'], kwargs['username'], kwargs['application_password'])
            extracted_contacts = extractor.fetch_contacts()
            contacts = extracted_contacts
        elif system == 'google':
            extractor = GoogleExtractor(kwargs['credentials_file'])
            extracted_contacts = extractor.fetch_contacts()
            contacts = extracted_contacts
        elif system == 'microsoft':
            # Accept access_token directly, or auto-fetch from env if not provided
            access_token = kwargs.get('access_token')
            extractor = MicrosoftExtractor(access_token)
            contacts = extractor.fetch_contacts()
        else:
            raise ValueError(f"Unknown system: {system}")

        # Ensure required keys exist in self.contacts
        for key in ['profiles', 'emails', 'phone_numbers', 'addresses']:
            if key not in self.contacts:
                self.contacts[key] = []
            else:
                # Deduplicate each list
                self.contacts[key] = list(dict.fromkeys(self.contacts[key]))

        # Update our internal data structure
        self.contacts['profiles'].extend([
            {
                'name': contact.get('name', ''),
                'emails': contact.get('emails', []),
                'phone_numbers': contact.get('phone_numbers', []),
                'addresses': contact.get('addresses', []),
                'source': system,
                'fetched_at': datetime.now().isoformat()
            }
            for contact in contacts.get('profiles', contacts)
        ])
        # Deduplicate profiles by name
        seen_names = set()
        unique_profiles = []
        for profile in self.contacts['profiles']:
            if profile['name'] and profile['name'] not in seen_names:
                unique_profiles.append(profile)
                seen_names.add(profile['name'])
        self.contacts['profiles'] = unique_profiles

        # Also update the individual collections
        for profile in self.contacts['profiles']:
            for email in profile.get('emails', []):
                if email and email not in self.contacts['emails']:
                    self.contacts['emails'].append(email)
            for phone in profile.get('phone_numbers', []):
                if phone and phone not in self.contacts['phone_numbers']:
                    self.contacts['phone_numbers'].append(phone)
            for address in profile.get('addresses', []):
                if address and address not in self.contacts['addresses']:
                    self.contacts['addresses'].append(address)

        return self.contacts

    def save_to_csv(self, filename="contacts.csv"):
        """
        Saves the fetched contacts to a CSV file.

        Args:
            filename (str): The name of the CSV file.
        """
        import csv
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['Name', 'Email', 'Phone', 'Address', 'Source', 'Fetched At']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write profiles
                for profile in self.contacts['profiles']:
                    base_row = {
                        'Name': profile.get('name', ''),
                        'Source': profile.get('source', ''),
                        'Fetched At': profile.get('fetched_at', '')
                    }
                    
                    # Write emails
                    for email in profile.get('emails', []):
                        row = base_row.copy()
                        row['Email'] = email
                        writer.writerow(row)
                    
                    # Write phone numbers
                    for phone in profile.get('phone_numbers', []):
                        row = base_row.copy()
                        row['Phone'] = phone
                        writer.writerow(row)
                    
                    # Write addresses
                    for address in profile.get('addresses', []):
                        row = base_row.copy()
                        row['Address'] = address
                        writer.writerow(row)
            
            logging.info(f"Saved contacts to {filename}")
        except Exception as e:
            logging.error(f"Error saving contacts to CSV: {e}")