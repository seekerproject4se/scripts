import os
import hashlib
import logging
import requests
from datetime import datetime
from utils import make_request  # Ensure make_request is imported correctly
from config import TOR_PROXY  # Import TOR_PROXY from config.py
import re

class FileDownloader:
    """
    A utility class to download files (e.g., PDFs) from URLs and save them to a specified directory.
    Includes duplicate detection using SHA-256 hashes and supports Tor proxy for anonymity.
    """

    @staticmethod
    def download_file(file_url, directory, allowed_extensions=None):
        """
        Downloads a file from the given URL and saves it to the specified directory.

        Args:
            file_url (str): The URL of the file to download.
            directory (str): The directory where the file will be saved.
            allowed_extensions (list): A list of allowed file extensions (e.g., ['.pdf']).

        Returns:
            str: The path to the downloaded file, or None if the download failed or was skipped.
        """
        try:
            logging.info(f"Attempting to download file from {file_url}")

            # Check if the file has an allowed extension
            file_ext = os.path.splitext(file_url)[1].lower()
            if allowed_extensions and file_ext not in allowed_extensions:
                logging.info(f"Skipping file with unsupported extension: {file_ext}")
                return None

            # Make the request using Tor proxy
            response = make_request(file_url, headers={}, proxies=TOR_PROXY, max_retries=5, backoff_factor=1)
            if response is None:
                response = make_request(file_url, headers={}, proxies=None, max_retries=5, backoff_factor=1)
            if response is None:
                logging.error(f"Failed to fetch file from {file_url}")
                return None

            response.raise_for_status()
            content = response.content
            new_file_hash = hashlib.sha256(content).hexdigest()

            # Ensure the directory exists
            os.makedirs(directory, exist_ok=True)

            # Check for duplicate files in the directory
            for existing_file in os.listdir(directory):
                full_path = os.path.join(directory, existing_file)
                if not os.path.isfile(full_path):
                    continue
                existing_hash = FileDownloader.calculate_file_hash(full_path)
                if existing_hash == new_file_hash:
                    logging.info(f"Duplicate file found for {file_url}, skipping download.")
                    return None

            # Generate a unique file name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            sanitized_name = re.sub(r'[^a-zA-Z0-9._-]', '_', os.path.basename(file_url))
            file_name = f"{timestamp}_{sanitized_name}"
            file_path = os.path.join(directory, file_name)

            # Save the file
            with open(file_path, 'wb') as file:
                file.write(content)

            logging.info(f"File downloaded and saved to: {file_path}")
            return file_path

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download file {file_url}: {e}")
            return None
        except OSError as e:
            logging.error(f"Error accessing directory {directory}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error while downloading file from {file_url}: {e}", exc_info=True)
            return None

    @staticmethod
    def calculate_file_hash(file_path):
        """
        Calculates the SHA-256 hash of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The SHA-256 hash of the file.
        """
        try:
            hash_obj = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            logging.error(f"Error calculating hash for file {file_path}: {e}")
            return None
