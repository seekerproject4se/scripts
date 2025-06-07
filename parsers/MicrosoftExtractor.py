import os
import requests
import logging
from datetime import datetime

class MicrosoftExtractor:
    def __init__(self, access_token=None):
        # Allow passing token directly, or fetch from env var
        self.access_token = access_token or os.environ.get("MS_GRAPH_TOKEN")
        if not self.access_token:
            # Optionally, auto-fetch a token using env credentials if not provided
            tenant_id = os.environ.get("MS_TENANT_ID")
            client_id = os.environ.get("MS_CLIENT_ID")
            client_secret = os.environ.get("MS_CLIENT_SECRET")
            if tenant_id and client_id and client_secret:
                token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
                data = {
                    "client_id": client_id,
                    "scope": "https://graph.microsoft.com/.default",
                    "client_secret": client_secret,
                    "grant_type": "client_credentials"
                }
                resp = requests.post(token_url, data=data)
                if resp.ok:
                    self.access_token = resp.json().get("access_token")
                else:
                    raise Exception(f"Failed to obtain Microsoft Graph token: {resp.text}")
            else:
                raise Exception("No Microsoft Graph access token or credentials provided.")
        
        # Initialize data structure with lists
        self.contacts = {
            'emails': [],
            'phone_numbers': [],
            'addresses': [],
            'profiles': []
        }

    def fetch_contacts(self):
        """
        Fetches contacts from Outlook using the Microsoft Graph API.

        Returns:
            list: A list of dictionaries containing contact information.
        """
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            url = 'https://graph.microsoft.com/v1.0/me/contacts'
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            contacts = response.json().get('value', [])
            for contact in contacts:
                # Create profile
                profile = {
                    'name': contact.get('displayName', ''),
                    'emails': [email['address'] for email in contact.get('emailAddresses', [])],
                    'phone_numbers': contact.get('businessPhones', []),
                    'addresses': [],  # Microsoft Graph API doesn't provide addresses
                    'source': 'outlook',
                    'fetched_at': datetime.now().isoformat()
                }
                
                # Update data structure
                self.contacts['profiles'].append(profile)
                
                # Update individual collections
                for email in profile['emails']:
                    if email not in self.contacts['emails']:
                        self.contacts['emails'].append(email)
                for phone in profile['phone_numbers']:
                    if phone not in self.contacts['phone_numbers']:
                        self.contacts['phone_numbers'].append(phone)

            # Deduplicate emails, phone_numbers, and profiles
            self.contacts['emails'] = list(dict.fromkeys(self.contacts['emails']))
            self.contacts['phone_numbers'] = list(dict.fromkeys(self.contacts['phone_numbers']))
            seen_names = set()
            unique_profiles = []
            for profile in self.contacts['profiles']:
                if profile['name'] and profile['name'] not in seen_names:
                    unique_profiles.append(profile)
                    seen_names.add(profile['name'])
            self.contacts['profiles'] = unique_profiles

            logging.info(f"Fetched {len(self.contacts['profiles'])} contacts from Outlook.")
            return self.contacts
        except Exception as e:
            logging.error(f"Error fetching Outlook contacts: {e}")
            return []