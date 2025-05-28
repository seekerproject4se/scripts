import requests
import logging
import time
from datetime import datetime
from .DataManager import DataManager  # Fixed import

class WordPressExtractor:
    def __init__(self, site_url, username, application_password, data_manager=None):
        self.site_url = site_url
        self.username = username
        self.application_password = application_password
        self.data_manager = data_manager or DataManager()
        self.contacts = self.data_manager.card_dict

    def fetch_contacts(self):
        """
        Fetches user data from the WordPress REST API, with 403 bypass handling.

        Returns:
            dict: A dictionary containing contact information with proper data structures.
        """
        url = f"{self.site_url}/wp-json/wp/v2/users"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        for attempt in range(5):  # Retry up to 5 times
            try:
                response = requests.get(url, auth=(self.username, self.application_password), headers=headers)
                response.raise_for_status()

                users = response.json()
                for user in users:
                    # Create profile using DataManager's structure
                    profile = {
                        'name': user.get('name', ''),
                        'source': 'wordpress',
                        'context': f"WordPress user profile for {user.get('name', '')}",
                        'type': 'profile',
                        'email': user.get('email', ''),
                        'phone': '',
                        'address': '',
                        'donation_amount': '',
                        'donation_context': '',
                        'fetched_at': datetime.now().isoformat()
                    }
                    
                    # Update data structure using DataManager's structure
                    self.data_manager.add_donor_profile(profile)
                    if user.get('email'):
                        self.data_manager.update_data({
                            'Emails': [user['email']],
                            'Profiles': [profile]
                        })

                logging.info(f"Fetched {len(self.contacts['profiles'])} contacts from WordPress.")
                return self.contacts

            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    logging.warning(f"403 Forbidden. Retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logging.error(f"HTTP error: {e}")
                    break
            except Exception as e:
                logging.error(f"Error fetching contacts from WordPress: {e}")
                break

        return self.contacts