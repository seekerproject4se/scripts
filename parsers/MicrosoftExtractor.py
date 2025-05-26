import requests
import logging

class MicrosoftExtractor:
    def __init__(self, access_token):
        self.access_token = access_token
        
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

            logging.info(f"Fetched {len(self.contacts['profiles'])} contacts from Outlook.")
            return self.contacts

            logging.info(f"Fetched {len(self.contacts)} contacts from Outlook.")
            return self.contacts
        except Exception as e:
            logging.error(f"Error fetching Outlook contacts: {e}")
            return []