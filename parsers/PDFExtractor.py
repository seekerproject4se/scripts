import logging
import re
import fitz  # PyMuPDF
import os
import hashlib
import requests
# Import key_data_patterns from config.py
from config import key_data_patterns

class PDFExtractor:
    @staticmethod
    def identify_and_download_pdf(pdf_url, save_directory, key_data_patterns):
        """
        Reads a PDF for key data and downloads it only if it contains the relevant data.
        Ensures no duplicate files are downloaded.

        Args:
            pdf_url (str): The URL of the PDF file.
            save_directory (str): The directory where the PDF file should be saved.
            key_data_patterns (dict): A dictionary of regex patterns to identify key data.

        Returns:
            tuple: (str: The path to the saved PDF file, dict: Extracted contact information)
        """
        if not pdf_url:
            logging.error("Invalid PDF URL provided.")
            return None, None

        try:
            # Fetch the PDF file content without saving it
            logging.info(f"Fetching PDF from URL: {pdf_url}")
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()

            # Open the PDF in memory
            pdf_document = fitz.open(stream=response.content, filetype="pdf")
            text = ""

            # Extract text from each page to identify key data
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                page_text = page.get_text()
                logging.debug(f"Extracted text from page {page_num + 1}: {page_text[:500]}")  # Log first 500 characters
                text += page_text

            pdf_document.close()

            # Initialize contact data structure
            contact_data = {
                'emails': [],
                'phone_numbers': [],
                'addresses': [],
                'profiles': []
            }

            # Extract contact information
            for pattern_name, pattern in key_data_patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    if pattern_name == 'email':
                        contact_data['emails'].extend(matches)
                    elif pattern_name == 'phone':
                        contact_data['phone_numbers'].extend(matches)
                    elif pattern_name == 'address':
                        contact_data['addresses'].extend(matches)

            # Create profile if we have any contact information
            if any(contact_data.values()):
                profile = {
                    'name': '',  # PDFs typically don't have names
                    'emails': contact_data['emails'],
                    'phone_numbers': contact_data['phone_numbers'],
                    'addresses': contact_data['addresses'],
                    'source': 'pdf',
                    'fetched_at': datetime.now().isoformat()
                }
                contact_data['profiles'].append(profile)

            # Check for key data
            if not PDFExtractor.contains_key_data(text, key_data_patterns):
                logging.info(f"PDF at {pdf_url} does not contain relevant data. Skipping download.")
                return None, contact_data

            # Ensure the save directory exists
            os.makedirs(save_directory, exist_ok=True)

            # Get the filename from the URL
            filename = os.path.basename(pdf_url)
            file_path = os.path.join(save_directory, filename)

            # Check for duplicates by comparing hashes
            file_hash = hashlib.md5(response.content).hexdigest()
            logging.debug(f"Hash of the new PDF: {file_hash}")
            for existing_file in os.listdir(save_directory):
                existing_file_path = os.path.join(save_directory, existing_file)
                with open(existing_file_path, 'rb') as f:
                    existing_file_hash = hashlib.md5(f.read()).hexdigest()
                    logging.debug(f"Hash of existing file {existing_file}: {existing_file_hash}")
                    if existing_file_hash == file_hash:
                        logging.info(f"Duplicate PDF detected: {pdf_url}")
                        return None, contact_data  # Skip downloading duplicate files

            # Save the PDF file
            with open(file_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
            logging.info(f"PDF downloaded and saved: {file_path}")
            return file_path, contact_data

            # Check for key data
            if not PDFExtractor.contains_key_data(text, key_data_patterns):
                logging.info(f"PDF at {pdf_url} does not contain relevant data. Skipping download.")
                return None

            # Ensure the save directory exists
            os.makedirs(save_directory, exist_ok=True)

            # Get the filename from the URL
            filename = os.path.basename(pdf_url)
            file_path = os.path.join(save_directory, filename)

            # Check for duplicates by comparing hashes
            file_hash = hashlib.md5(response.content).hexdigest()
            logging.debug(f"Hash of the new PDF: {file_hash}")
            for existing_file in os.listdir(save_directory):
                existing_file_path = os.path.join(save_directory, existing_file)
                with open(existing_file_path, 'rb') as f:
                    existing_file_hash = hashlib.md5(f.read()).hexdigest()
                    logging.debug(f"Hash of existing file {existing_file}: {existing_file_hash}")
                    if existing_file_hash == file_hash:
                        logging.info(f"Duplicate PDF detected: {pdf_url}")
                        return None  # Skip downloading duplicate files

            # Save the PDF file
            with open(file_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
            logging.info(f"PDF downloaded and saved: {file_path}")
            return file_path

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch PDF from {pdf_url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error processing PDF from {pdf_url}: {e}", exc_info=True)
            return None

    @staticmethod
    def contains_key_data(text, key_data_patterns):
        """
        Checks if the given text contains any of the key data patterns.

        Args:
            text (str): The text content of the PDF.
            key_data_patterns (dict): A dictionary of regex patterns to identify key data.

        Returns:
            bool: True if any key data is found, False otherwise.
        """
        logging.debug(f"Checking for key data in text: {text[:500]}")  # Log first 500 characters
        for key, pattern in key_data_patterns.items():
            logging.debug(f"Checking pattern for {key}: {pattern}")
            if re.search(pattern, text):
                logging.info(f"Found key data ({key}) in PDF.")
                return True
        return False
        logging.info("No key data found in PDF.")
        return False

