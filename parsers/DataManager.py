import logging
import os
import json
from datetime import datetime

class DataManager:
    def __init__(self):
        # Define comprehensive data structure with proper types
        self.card_dict = {
            'Profiles': [],       # List of profile dictionaries
            'Emails': [],         # List of email strings
            'PhoneNumbers': [],   # List of phone number strings
            'Addresses': [],      # List of address strings
            'Donations': [],      # List of donation dictionaries
            'Names': [],          # List of name strings
            'PDFLinks': [],       # List of PDF link strings
            'Entities': [],       # List of entity dictionaries
            'Donors': []          # List of donor dictionaries
        }
        logging.info("Initialized DataManager with comprehensive data structure")

    @staticmethod
    def clean_data(data):
        """
        Clean and validate the data structure to ensure consistency.
        
        Args:
            data (dict): Input data to clean
            
        Returns:
            dict: Cleaned and validated data
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        # Log the incoming data structure
        logging.debug(f"Cleaning data: {json.dumps(data, default=str)}")

        # Define allowed fields and their types
        allowed_fields = {
            'Profiles': list,
            'Emails': list,
            'PhoneNumbers': list,
            'Addresses': list,
            'Donations': list,
            'Names': list,
            'PDFLinks': list,
            'Entities': list,
            'Donors': list
        }

        cleaned_data = {}
        
        # Clean each field
        for field, expected_type in allowed_fields.items():
            if field in data:
                value = data[field]
                logging.debug(f"Processing field {field} with value: {value}")
                
                # Convert any non-list values to lists
                if not isinstance(value, expected_type):
                    logging.debug(f"Converting {field} to list")
                    if isinstance(value, set):
                        value = list(value)
                    elif isinstance(value, dict):
                        value = [value]
                    elif isinstance(value, str):
                        value = [value]
                    else:
                        try:
                            value = list(value)
                        except TypeError:
                            logging.debug(f"Type error converting {field}, using single item list")
                            value = [value]
                
                # Ensure we have a list
                if not isinstance(value, list):
                    value = [value]
                
                if field == 'Profiles':
                    cleaned_profiles = []
                    for profile in value:
                        if isinstance(profile, dict):
                            # Convert any nested sets to lists
                            for key, val in profile.items():
                                if isinstance(val, set):
                                    logging.debug(f"Converting nested set in profile {key}")
                                    profile[key] = list(val)
                            cleaned_profiles.append(profile)
                    value = cleaned_profiles
                elif field in ['Emails', 'PhoneNumbers', 'Addresses', 'Names', 'PDFLinks']:
                    # Convert to strings and remove duplicates
                    value = list(dict.fromkeys(str(item) for item in value))
                elif field == 'Donors':
                    # Special handling for Donors field
                    cleaned_donors = []
                    for donor in value:
                        if isinstance(donor, dict):
                            # Convert any nested sets to lists
                            for key, val in donor.items():
                                if isinstance(val, set):
                                    logging.debug(f"Converting nested set in donor {key}")
                                    donor[key] = list(val)
                            cleaned_donors.append(donor)
                    value = cleaned_donors
                
                cleaned_data[field] = value
                logging.debug(f"Cleaned {field}: {value}")

        logging.debug(f"Final cleaned data: {json.dumps(cleaned_data, default=str)}")
        return cleaned_data

    def update_data(self, data):
        """
        Update the card_dict with new data, ensuring no duplicates and validating input.

        Args:
            data (dict): A dictionary containing new data to merge.
        """
        logging.info(f"Updating card_dict with new data")

        try:
            # First clean the incoming data to ensure consistency
            cleaned_data = self.clean_data(data)

            # Safeguard: Only add truly new items (by unique key) to each field
            for field in self.card_dict:
                if field in cleaned_data:
                    # Ensure we have a list
                    if not isinstance(cleaned_data[field], list):
                        cleaned_data[field] = [cleaned_data[field]]
                    # Only add items not already present
                    if field in ['Profiles', 'Donors']:
                        # For profiles/donors, use 'name' as unique key
                        existing_names = {item.get('name') for item in self.card_dict[field] if isinstance(item, dict)}
                        for item in cleaned_data[field]:
                            if isinstance(item, dict) and item.get('name') and item.get('name') not in existing_names:
                                self.card_dict[field].append(item)
                                existing_names.add(item.get('name'))
                    else:
                        # For simple lists, only add new unique items
                        existing_items = set(self.card_dict[field])
                        for item in cleaned_data[field]:
                            if isinstance(item, dict):
                                key = str(item)
                            else:
                                key = str(item)
                            if key not in existing_items:
                                self.card_dict[field].append(item)
                                existing_items.add(key)
            logging.info("Safeguard: Only new data added to card_dict.")
        except Exception as e:
            logging.error(f"Error updating data: {str(e)}")
            raise

        logging.debug(f"Updated card_dict")

    def add_donor_profile(self, profile):
        """
        Add a new donor profile to the card_dict.

        Args:
            profile (dict): A donor profile dictionary.
        """
        # Clean the profile data
        profile = self.clean_data({'Profiles': [profile]})['Profiles'][0]

        # Check for existing profile with same name
        existing_profile = None
        for idx, existing in enumerate(self.card_dict['Profiles']):
            if existing.get('name') == profile.get('name'):
                existing_profile = existing
                break

        if existing_profile:
            # Merge profiles with proper list handling
            # Remove duplicates while merging
            existing_profile['emails'] = list(dict.fromkeys(existing_profile['emails'] + profile['emails']))
            existing_profile['phone_numbers'] = list(dict.fromkeys(existing_profile['phone_numbers'] + profile['phone_numbers']))
            existing_profile['addresses'] = list(dict.fromkeys(existing_profile['addresses'] + profile['addresses']))
            
            # For donations, we want to keep all entries
            existing_profile['Donations'].extend(profile['Donations'])
            
            # Update timestamps
            existing_profile['last_seen'] = max(
                datetime.fromisoformat(existing_profile.get('last_seen', '1970-01-01T00:00:00')),
                datetime.fromisoformat(profile.get('last_seen', '1970-01-01T00:00:00'))
            ).isoformat()
            
            # Ensure all lists are unique
            existing_profile['Emails'] = list(dict.fromkeys(existing_profile['Emails']))
            existing_profile['PhoneNumbers'] = list(dict.fromkeys(existing_profile['PhoneNumbers']))
            existing_profile['Addresses'] = list(dict.fromkeys(existing_profile['Addresses']))
            logging.info(f"Merged donor profile: {profile['name']}")
        else:
            # Add new profile
            self.card_dict['Profiles'].append(profile)
            logging.info(f"Added new donor profile: {profile['name']}")

    def save_to_file(self, directory):
        """
        Save the card_dict to a JSON file in the specified directory.
        If the file exists, merge the new data with the existing data, but do not overwrite existing entries.

        Args:
            directory (str): The directory where the file should be saved.
        """
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, 'extracted_data.json')
        
        try:
            # If file exists, load existing data and merge
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # Only add new data (safeguard)
                self.update_data(existing_data)
        except Exception as e:
            logging.warning(f"Error loading existing data: {e}")

        # Prepare data for JSON serialization
        serializable_dict = {
            'Profiles': self.card_dict['Profiles'],
            'Emails': self.card_dict['Emails'],
            'PhoneNumbers': self.card_dict['PhoneNumbers'],
            'Donations': self.card_dict['Donations'],
            'Names': self.card_dict['Names'],
            'Addresses': self.card_dict['Addresses'],
            'PDFLinks': self.card_dict['PDFLinks'],
            'Entities': self.card_dict['Entities']
        }
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_dict, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Saved data to {filename}")

    def consolidate_data(self, data_list):
        """
        Consolidates data from multiple sources, ensuring proper associations and deduplication.

        Args:
            data_list (list): List of data dictionaries to consolidate.
        """
        consolidated_data = {
            'Profiles': [],
            'Emails': set(),
            'Phones': set(),
            'Donations': [],  # Use list for dictionaries
            'Names': set(),
            'Addresses': set(),
            'PDFLinks': set(),
            'Entities': []
        }

        for data in data_list:
            # Add donor profiles
            if 'Profiles' in data:
                for profile in data['Profiles']:
                    for idx, existing in enumerate(consolidated_data['Profiles']):
                        if existing['name'] == profile['name']:
                            existing_profile = existing
                            break

                    if existing_profile:
                        # Merge profiles
                        existing_profile['emails'].update(profile['emails'])
                        existing_profile['phone_numbers'].update(profile['phone_numbers'])
                        existing_profile['addresses'].update(profile['addresses'])
                        existing_profile['donations'].extend(profile['donations'])
                        existing_profile['last_seen'] = max(
                            datetime.fromisoformat(existing_profile['last_seen']),
                            datetime.fromisoformat(profile['last_seen'])
                        ).isoformat()
                    else:
                        consolidated_data['Profiles'].append(profile)

            # Add other data
            emails = data.get('Emails', [])
            for email in emails:
                if email not in consolidated_data['Emails']:
                    consolidated_data['Emails'].append(email)

            phones = data.get('Phones', [])
            for phone in phones:
                if phone not in consolidated_data['Phones']:
                    consolidated_data['Phones'].append(phone)

            donations = data.get('Donations', [])
            for donation in donations:
                if donation not in consolidated_data['Donations']:
                    consolidated_data['Donations'].append(donation)

            names = data.get('Names', [])
            for name in names:
                if name not in consolidated_data['Names']:
                    consolidated_data['Names'].append(name)

            addresses = data.get('Addresses', [])
            for address in addresses:
                if address not in consolidated_data['Addresses']:
                    consolidated_data['Addresses'].append(address)

            pdf_links = data.get('PDFLinks', [])
            for pdf_link in pdf_links:
                if pdf_link not in consolidated_data['PDFLinks']:
                    consolidated_data['PDFLinks'].append(pdf_link)

            entities = data.get('Entities', [])
            for entity in entities:
                if entity not in consolidated_data['Entities']:
                    consolidated_data['Entities'].append(entity)

        return consolidated_data