import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
from urllib.parse import urljoin, urlparse
from flask import Flask, request, jsonify
import logging
import time
import PyPDF2

app = Flask(__name__)

# Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG)

@app.route('/')
def home():
    return "Hello, this is your Flask app running through Nginx!"

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/search', methods=['POST'])
def search():
    try:
        urls = request.json.get('urls')
        if not urls:
            return jsonify({"error": "URLs are required"}), 400
        
        results = []
        for url in urls:
            donor_data = crawl_site(url)
            if donor_data:
                cleaned_data = clean_data(donor_data)
                results.append({"url": url, "data": cleaned_data})
                save_to_excel(url, cleaned_data)
            else:
                results.append({"url": url, "error": "No data found"})
        
        return jsonify(results), 200
    except Exception as e:
        app.logger.error(f"Error in search function: {e}")
        return jsonify({"error": "An error occurred during processing"}), 500

def crawl_site(start_url):
    visited = set()
    to_visit = [start_url]
    all_data = []

    while to_visit:
        url = to_visit.pop(0)
        app.logger.info(f"Visiting URL: {url}")
        if url in visited:
            continue
        visited.add(url)
        
        donor_data = fetch_donor_data(url)
        if donor_data:
            all_data.append(donor_data)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            response = requests.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()
            response.encoding = 'utf-8'
            app.logger.info(f"Fetched content from {url}: {response.content[:100]}")

            # Check Content-Type
            content_type = response.headers.get('Content-Type', '')
            logging.info(f"Content-Type: {content_type}")

            # Use appropriate parser based on Content-Type
            if 'xml' in content_type:
                soup = BeautifulSoup(response.content, 'xml')
            elif 'html' in content_type:
                soup = BeautifulSoup(response.content, 'html.parser')
            else:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                except Exception as e:
                    logging.error(f"html.parser failed: {e}")
                    try:
                        soup = BeautifulSoup(response.content, 'lxml')
                    except Exception as e:
                        logging.error(f"lxml parser failed: {e}")
                        try:
                            soup = BeautifulSoup(response.content, 'html5lib')
                        except Exception as e:
                            logging.error(f"html5lib parser failed: {e}")
                            raise e

            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                if urlparse(full_url).netloc == urlparse(start_url).netloc and full_url not in visited:
                    to_visit.append(full_url)
        except requests.RequestException as e:
            app.logger.error(f"Failed to fetch page {url}: {e}")

    combined_data = combine_data(all_data)
    return combined_data

def combine_data(all_data):
    combined_data = {}
    for data in all_data:
        for key, value in data.items():
            if key not in combined_data:
                combined_data[key] = [value] if not isinstance(value, list) else value
            else:
                if not isinstance(combined_data[key], list):
                    combined_data[key] = [combined_data[key]]
                combined_data[key].extend(value if isinstance(value, list) else [value])
    return combined_data

def fetch_donor_data(url):
    try:
        if url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.json', '.xml', '.db', '.sql')):
            app.logger.info(f"Checking for existing file for non-HTML URL: {url}")
            filename = os.path.basename(url)
            folder_name = urlparse(url).netloc
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
            
            file_path = os.path.join(folder_name, filename)
            
            if os.path.exists(file_path):
                app.logger.info(f"File already exists: {file_path}. Skipping download.")
                return {"downloaded_files": [file_path]}
            
            app.logger.info(f"Downloading non-HTML URL: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            return {"downloaded_files": [file_path]}

        if not re.match(r'^https?://', url) or url in ['javascript:void(0)', '#']:
            app.logger.error(f"Invalid URL: {url}")
            return []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        retries = 3
        for _ in range(retries):
            response = requests.get(url, headers=headers, allow_redirects=True)
            if response.status_code == 403:
                app.logger.error(f"Access denied for {url}, retrying...")
                time.sleep(5)
                continue
            else:
                break

        response.raise_for_status()
        final_url = response.url
        app.logger.info(f"Final URL after redirection: {final_url}")

        response.encoding = 'utf-8'

        try:
            soup = BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logging.error(f"html.parser failed: {e}")
            try:
                soup = BeautifulSoup(response.content, 'lxml')
            except Exception as e:
                logging.error(f"lxml parser failed: {e}")
                try:
                    soup = BeautifulSoup(response.content, 'html5lib')
                except Exception as e:
                    logging.error(f"html5lib parser failed: {e}")
                    raise e

        app.logger.info(f"Fetched HTML content from {final_url}: {soup.prettify()[:500]}")

        data = {}

        emails = soup.find_all(string=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'))
        app.logger.info(f"Found {len(emails)} email addresses")

        for email in emails:
            parent = email.parent
            text = parent.get_text(strip=True)
            app.logger.debug(f"Processing element text: {text}")

            if 'name' in text.lower():
                data.setdefault('names', []).append(text)
            elif 'address' in text.lower():
                data.setdefault('addresses', []).append(text)
            elif re.search(r'\b\d{5}(?:-\d{4})?\b', text):
                data.setdefault('zips', []).append(text)
            elif re.search(r'contribution|donation|gift', text, re.I):
                data.setdefault('contributions', []).append(text)
            elif re.search(r'\b(?:\+?1[-.\s]?)?$?\d{3}$?[-.\s]?\d{3}[-.\s]?\d{4}\b', text):
                data.setdefault('phones', []).append(text)

            data.setdefault('emails', []).append(email)

        app.logger.info(f"Extracted data: {data}")

        return data
    except requests.RequestException as e:
        app.logger.error(f"Failed to fetch data from {url}: {e}")
        return {}
    except Exception as e:
        app.logger.error(f"Error fetching donor data from {url}: {e}")
        return {}
def clean_data(data):
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, list):
            cleaned_data[key] = [v.strip() for v in value if v.strip()]
        else:
            cleaned_data[key] = value.strip()
    return cleaned_data

def save_to_excel(url, data):
    filename = f"{url.replace('http://', '').replace('https://', '').replace('/', '_')}.xlsx"
    
    for key in data:
        if not isinstance(data[key], list):
            data[key] = [data[key]]
    
    try:
        if os.path.exists(filename):
            existing_data = pd.read_excel(filename)
            new_data = pd.DataFrame(data)
            combined_data = pd.concat([existing_data, new_data]).drop_duplicates().reset_index(drop=True)
            combined_data.to_excel(filename, index=False)
        else:
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False)
        
        app.logger.info(f"Data saved to {filename}")
    except Exception as e:
        app.logger.error(f"Failed to save data to {filename}: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=5001)
