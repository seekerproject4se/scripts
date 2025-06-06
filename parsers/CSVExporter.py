import os
import csv
import logging
import re  # Added for validation and cleaning
from urllib.parse import urlparse
from datetime import datetime

class CSVExporter:
    """
    A utility class to export extracted data to a CSV file.
    """

    @staticmethod
    def is_valid_email(email):
        """
        Validate an email address using a regex pattern.
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None

    @staticmethod
    def normalize_phone_number(phone):
        """
        Normalize phone numbers to a standard format (e.g., (123) 456-7890).
        """
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(phone_pattern, phone)
        return match.group(0) if match else None

    @staticmethod
    def clean_field(field):
        """
        Remove unwanted characters from a field.
        """
        return re.sub(r'[^\w\s]', '', field).strip()

    @staticmethod
    def save_csv(data_dict, url):
        """
        Saves the extracted data to a CSV file named after the URL of the site being scraped.

        Args:
            data_dict (dict): The dictionary containing the extracted data.
            url (str): The URL of the site being scraped.
        """
        try:
            # Create a sanitized filename from the URL
            if url:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace('.', '_') if parsed_url.netloc else 'unknown_domain'
            else:
                domain = 'unknown_domain'
            directory = os.path.join('DATA', domain)
            os.makedirs(directory, exist_ok=True)
            filename = os.path.join(directory, f"{domain}_donor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            
            # Prepare the data for CSV export
            rows = []
            
            # Add profiles and their associated data
            for profile in data_dict.get('Profiles', []):
                if not isinstance(profile, dict):
                    continue
                
                # Create base row with profile info
                base_row = {
                    'Name': profile.get('name', ''),
                    'First Name': profile.get('first_name', ''),
                    'Last Name': profile.get('last_name', ''),
                    'Source URL': profile.get('source', ''),
                    'Type': 'profile',
                    'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Email': '',
                    'Phone': '',
                    'Address': '',
                    'Donation Amount': '',
                    'Donation Context': profile.get('context', '')
                }

                # Add emails for this profile
                emails = profile.get('Emails', [])
                if not isinstance(emails, list):
                    emails = [emails] if emails else []
                for email in emails:
                    if isinstance(email, str) and CSVExporter.is_valid_email(email):
                        row = base_row.copy()
                        row['Email'] = email
                        row['Type'] = 'email'
                        rows.append(row)

                # Add phone numbers for this profile
                phones = profile.get('PhoneNumbers', [])
                if not isinstance(phones, list):
                    phones = [phones] if phones else []
                for phone in phones:
                    if isinstance(phone, str):
                        normalized_phone = CSVExporter.normalize_phone_number(phone)
                        if normalized_phone:
                            row = base_row.copy()
                            row['Phone'] = normalized_phone
                            row['Type'] = 'phone'
                            rows.append(row)

                # Add addresses for this profile
                addresses = profile.get('Addresses', [])
                if not isinstance(addresses, list):
                    addresses = [addresses] if addresses else []
                for address in addresses:
                    if isinstance(address, str):
                        cleaned_address = CSVExporter.clean_field(address)
                        if cleaned_address:
                            row = base_row.copy()
                            row['Address'] = cleaned_address
                            row['Type'] = 'address'
                            rows.append(row)

                # Add donations for this profile
                donations = profile.get('Donations', [])
                if not isinstance(donations, list):
                    donations = [donations] if donations else []
                for donation in donations:
                    if isinstance(donation, dict) and 'amount' in donation:
                        row = base_row.copy()
                        row['Donation Amount'] = donation['amount']
                        row['Donation Context'] = donation.get('context', '')
                        row['Type'] = 'donation'
                        rows.append(row)

            # Add standalone emails
            for email in data_dict.get('Emails', []):
                if isinstance(email, str) and CSVExporter.is_valid_email(email):
                    row = {
                        'Name': '',
                        'First Name': '',
                        'Last Name': '',
                        'Source URL': url,
                        'Type': 'email',
                        'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Email': email,
                        'Phone': '',
                        'Address': '',
                        'Donation Amount': '',
                        'Donation Context': ''
                    }
                    rows.append(row)

            # Add standalone phone numbers
            for phone in data_dict.get('PhoneNumbers', []):
                if isinstance(phone, str):
                    normalized_phone = CSVExporter.normalize_phone_number(phone)
                    if normalized_phone:
                        row = {
                            'Name': '',
                            'First Name': '',
                            'Last Name': '',
                            'Source URL': url,
                            'Type': 'phone',
                            'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Email': '',
                            'Phone': normalized_phone,
                            'Address': '',
                            'Donation Amount': '',
                            'Donation Context': ''
                        }
                        rows.append(row)

            # Add standalone addresses
            for address in data_dict.get('Addresses', []):
                if isinstance(address, str):
                    cleaned_address = CSVExporter.clean_field(address)
                    if cleaned_address:
                        row = {
                            'Name': '',
                            'First Name': '',
                            'Last Name': '',
                            'Source URL': url,
                            'Type': 'address',
                            'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Email': '',
                            'Phone': '',
                            'Address': cleaned_address,
                            'Donation Amount': '',
                            'Donation Context': ''
                        }
                        rows.append(row)

            # Add standalone donations
            for donation in data_dict.get('Donations', []):
                if isinstance(donation, dict) and 'amount' in donation:
                    row = {
                        'Name': '',
                        'First Name': '',
                        'Last Name': '',
                        'Source URL': url,
                        'Type': 'donation',
                        'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Email': '',
                        'Phone': '',
                        'Address': '',
                        'Donation Amount': donation['amount'],
                        'Donation Context': donation.get('context', '')
                    }
                    rows.append(row)
            
            # Write to CSV
            if rows:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'Name', 'First Name', 'Last Name', 'Source URL', 'Type', 'Date',
                        'Email', 'Phone', 'Address',
                        'Donation Amount', 'Donation Context'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                logging.info(f"Successfully saved data to {filename}")
                return filename
            else:
                logging.warning("No data to export")
                return None
                
        except Exception as e:
            logging.error(f"Error saving CSV: {str(e)}", exc_info=True)
            return None

            # Validate and clean data
            data_dict['Emails'] = [email for email in data_dict['Emails'] if CSVExporter.is_valid_email(email)]
            data_dict['Phones'] = [CSVExporter.normalize_phone_number(phone) for phone in data_dict['Phones'] if CSVExporter.normalize_phone_number(phone)]
            for key in data_dict:
                data_dict[key] = [CSVExporter.clean_field(value) for value in data_dict[key]]

            # Extract the base domain from the URL
            parsed_url = urlparse(url)
            base_domain = parsed_url.netloc.replace(".", "_")  # e.g., www_fftc_org
            logging.debug(f"Base domain extracted: {base_domain}")

            # Generate the directory and file path
            directory = os.path.join("data", base_domain)  # Save under data/<base_domain>
            logging.debug(f"Ensuring directory exists: {directory}")
            os.makedirs(directory, exist_ok=True)
            if not os.path.exists(directory):
                logging.error(f"Failed to create directory: {directory}")
                return
            file_path = os.path.join(directory, f"{base_domain}.csv")  # Single CSV file per domain
            logging.debug(f"File path being used: {file_path}")

            # Check if the file already exists
            file_exists = os.path.isfile(file_path)

            # Dynamically determine fieldnames based on the data_dict
            fieldnames = []
            for key, values in data_dict.items():
                if isinstance(values, list) and values:  # Only include non-empty lists
                    fieldnames.append(key)
            logging.debug(f"Dynamic fieldnames determined: {fieldnames}")

            # Open the CSV file in append mode
            with open(file_path, mode='a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write the header only if the file is new
                if not file_exists:
                    writer.writeheader()

                # Write each row of data to the CSV file
                max_length = max(len(values) for values in data_dict.values() if isinstance(values, list))
                for i in range(max_length):
                    row = {field: (data_dict[field][i] if i < len(data_dict[field]) else "N/A") for field in fieldnames}
                    writer.writerow(row)

            logging.info(f"Data successfully exported to CSV: {file_path}")

        except Exception as e:
            logging.error(f"Error exporting data to CSV: {e}", exc_info=True)
