from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging
from .DataManager import DataManager
from datetime import datetime

class GoogleExtractor:
    def __init__(self, credentials_file, data_manager=None):
        self.credentials_file = credentials_file
        self.data_manager = data_manager or DataManager()
        self.contacts = self.data_manager.card_dict

    def fetch_contacts(self):
        """
        Fetches contacts from Gmail using the Google People API.

        Returns:
            list: A list of dictionaries containing contact information.
        """
        profiles = []
        try:
            creds = Credentials.from_authorized_user_file(self.credentials_file, scopes=[
                'https://www.googleapis.com/auth/contacts.readonly'
            ])
            service = build('people', 'v1', credentials=creds)

            # Fetch connections (contacts)
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses,phoneNumbers,addresses'
            ).execute()

            while results:
                connections = results.get('connections', [])
                for person in connections:
                    # Create profile using DataManager's structure
                    profile = {
                        'name': person['names'][0].get('displayName', '') if 'names' in person else '',
                        'email': person.get('emailAddresses', [{}])[0].get('value', '') if person.get('emailAddresses') else '',
                        'phone': person.get('phoneNumbers', [{}])[0].get('value', '') if person.get('phoneNumbers') else '',
                        'address': person.get('addresses', [{}])[0].get('formattedValue', '') if person.get('addresses') else '',
                        'source': 'gmail',
                        'fetched_at': datetime.now().isoformat()
                    }
                    profiles.append(profile)
                    # Update data structure using DataManager's structure
                    self.data_manager.add_donor_profile(profile)
                    self.data_manager.update_data({
                        'Emails': [email.get('value', '') for email in person.get('emailAddresses', [])],
                        'PhoneNumbers': [phone.get('value', '') for phone in person.get('phoneNumbers', [])],
                        'Addresses': [address.get('formattedValue', '') for address in person.get('addresses', [])],
                        'DonorProfiles': [profile]
                    })
                    
                    # Update individual collections
                    for email in profile['emails']:
                        if email not in self.contacts['emails']:
                            self.contacts['emails'].append(email)
                    for phone in profile['phone_numbers']:
                        if phone not in self.contacts['phone_numbers']:
                            self.contacts['phone_numbers'].append(phone)
                    for address in profile['addresses']:
                        if address not in self.contacts['addresses']:
                            self.contacts['addresses'].append(address)

                # Check for nextPageToken to fetch additional contacts
                next_page_token = results.get('nextPageToken')
                if next_page_token:
                    results = service.people().connections().list(
                        resourceName='people/me',
                        pageSize=1000,
                        personFields='names,emailAddresses,phoneNumbers,addresses',
                        pageToken=next_page_token
                    ).execute()
                else:
                    break

            logging.info(f"Fetched {len(profiles)} contacts from Gmail.")
            return profiles

        except Exception as e:
            logging.error(f"Error fetching Gmail contacts: {e}")
            return profiles

        # Check for nextPageToken to fetch additional contacts
        next_page_token = results.get('nextPageToken')
        if next_page_token:
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses,phoneNumbers,addresses',
                pageToken=next_page_token
            ).execute()
        else:
            return profiles