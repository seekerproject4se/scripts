import argparse
import logging
from flask import Flask, request, jsonify
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from parsers import HTMLParser, DataManager, CSVExporter, ContactParser
from utils import get_sanitized_url_directory, save_html_content, fetch_html, run_puppeteer_script
from routes import setup_routes
from parsers.EmailExtractor import EmailExtractor
from parsers.Parser import Parser
import glob
import json
import os
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

session = HTMLSession()

def find_latest_json():
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DATA')
    json_files = glob.glob(os.path.join(DATA_DIR, '**', 'extracted_data.json'), recursive=True)
    if not json_files:
        return None
    return max(json_files, key=os.path.getmtime)

def find_latest_email_csv():
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DATA')
    csv_files = glob.glob(os.path.join(DATA_DIR, '**', 'email_extracted.csv'), recursive=True)
    if not csv_files:
        return None
    return max(csv_files, key=os.path.getmtime)

def merge_profiles(web_json_path, email_csv_path, output_path):
    # Load web data
    web_donors = []
    if web_json_path:
        with open(web_json_path, 'r') as f:
            web_data = json.load(f)
        web_donors = web_data.get('Donors', [])
    # Load email data (CSV)
    import csv
    email_donors = []
    if email_csv_path:
        with open(email_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name') or row.get('Name')
                email = row.get('email') or row.get('Email')
                phone = row.get('phone') or row.get('Phone')
                if name or email or phone:
                    email_donors.append({
                        'name': name,
                        'emails': [email] if email else [],
                        'phones': [phone] if phone else []
                    })
    # Deduplicate by (name, email, phone)
    seen = set()
    merged = []
    for donor in web_donors + email_donors:
        key = (donor.get('name'), tuple(donor.get('emails', [])), tuple(donor.get('phones', [])))
        if key not in seen:
            merged.append(donor)
            seen.add(key)
    # Save merged output
    with open(output_path, 'w') as f:
        json.dump({'Donors': merged}, f, indent=2)
    print(f"Merged donor/contact profiles saved to: {output_path}")

@app.route('/extract/microsoft', methods=['POST'])
def extract_microsoft_contacts():
    data = request.get_json()
    access_token = data.get('access_token')
    if not access_token:
        return jsonify({'error': 'Missing access_token in request body'}), 400
    contact_parser = ContactParser()
    try:
        ms_contacts = contact_parser.fetch_contacts(
            system='microsoft',
            access_token=access_token
        )
        # Optionally save to CSV
        contact_parser.save_to_csv("microsoft_contacts.csv")
        return jsonify({'contacts': ms_contacts}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    parser_arg = argparse.ArgumentParser(description='Run the Flask app, scan a website, or extract from email.')
    parser_arg.add_argument('--mode', choices=['runserver', 'scan', 'email'], default='runserver', help='Mode: runserver, scan, or email')
    parser_arg.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the app on.')
    parser_arg.add_argument('--port', type=int, default=5001, help='Port to run the app on.')
    parser_arg.add_argument('--url', type=str, help='Target URL for scanning')
    parser_arg.add_argument('--max-depth', type=int, default=2, help='Max crawl depth')
    parser_arg.add_argument('--keywords', nargs='*', help='Optional keywords to filter URLs')
    parser_arg.add_argument('--email-host', type=str, help='IMAP host for email extraction')
    parser_arg.add_argument('--email-user', type=str, help='IMAP username for email extraction')
    parser_arg.add_argument('--email-pass', type=str, help='IMAP password for email extraction')
    parser_arg.add_argument('--email-folder', type=str, default='INBOX', help='IMAP folder to parse')
    parser_arg.add_argument('--email-dir', type=str, help='Directory of .eml/.mbox files for file-based extraction')
    parser_arg.add_argument('--wp-site-url', type=str, help='WordPress site URL for contact extraction')
    parser_arg.add_argument('--wp-username', type=str, help='WordPress username for contact extraction')
    parser_arg.add_argument('--wp-app-password', type=str, help='WordPress application password for contact extraction')
    parser_arg.add_argument('--ms-access-token', type=str, help='Microsoft Graph API access token for contact extraction')
    args = parser_arg.parse_args()

    if args.mode == 'runserver':
        setup_routes(app)
        # Example: Using ContactParser to fetch Gmail contacts
        contact_parser = ContactParser()
        gmail_contacts = contact_parser.fetch_contacts(
            system='google',
            credentials_file='credentials.json'
        )
        contact_parser.save_to_csv("gmail_contacts.csv")
        # Optionally fetch WordPress contacts if args provided
        if args.wp_site_url and args.wp_username and args.wp_app_password:
            wp_contacts = contact_parser.fetch_contacts(
                system='wordpress',
                site_url=args.wp_site_url,
                username=args.wp_username,
                application_password=args.wp_app_password
            )
            contact_parser.save_to_csv("wordpress_contacts.csv")
        # Optionally fetch Microsoft contacts if access token provided
        if args.ms_access_token:
            ms_contacts = contact_parser.fetch_contacts(
                system='microsoft',
                access_token=args.ms_access_token
            )
            contact_parser.save_to_csv("microsoft_contacts.csv")
        app.run(host=args.host, port=args.port)
    elif args.mode == 'scan':
        if not args.url:
            print("Please provide a --url to scan.")
            exit(1)
        parser = Parser()
        parser.crawl_site(
            start_url=args.url,
            max_depth=args.max_depth,
            keywords=args.keywords
        )
        print("Scan complete. Data saved.")
        # --- Automatic aggregation ---
        web_json = find_latest_json()
        email_csv = find_latest_email_csv()
        if web_json or email_csv:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DATA')
            output_path = os.path.join(DATA_DIR, f'merged_contacts_{timestamp}.json')
            merge_profiles(web_json, email_csv, output_path)
        else:
            print('No data to merge.')
        # Add WordPress extraction if args provided
        if args.wp_site_url and args.wp_username and args.wp_app_password:
            contact_parser = ContactParser()
            wp_contacts = contact_parser.fetch_contacts(
                system='wordpress',
                site_url=args.wp_site_url,
                username=args.wp_username,
                application_password=args.wp_app_password
            )
            contact_parser.save_to_csv("wordpress_contacts.csv")
        # Add Microsoft extraction if access token provided
        if args.ms_access_token:
            contact_parser = ContactParser()
            ms_contacts = contact_parser.fetch_contacts(
                system='microsoft',
                access_token=args.ms_access_token
            )
            contact_parser.save_to_csv("microsoft_contacts.csv")
    elif args.mode == 'email':
        extractor = EmailExtractor(
            host=args.email_host,
            username=args.email_user,
            password=args.email_pass
        )
        if args.email_host and args.email_user and args.email_pass:
            extractor.connect_to_email()
            extractor.parse_emails(folder=args.email_folder)
            extractor.save_to_csv(args.email_user or 'email_contacts')
            print("Email extraction complete. Data saved to CSV.")
        elif args.email_dir:
            extractor.parse_email_files(args.email_dir)
            extractor.save_to_csv(args.email_dir)
            print("Email file extraction complete. Data saved to CSV.")
        else:
            print("Please provide either IMAP credentials or a directory of email files for email extraction.")
        # --- Automatic aggregation ---
        web_json = find_latest_json()
        email_csv = find_latest_email_csv()
        if web_json or email_csv:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DATA')
            output_path = os.path.join(DATA_DIR, f'merged_contacts_{timestamp}.json')
            merge_profiles(web_json, email_csv, output_path)
        else:
            print('No data to merge.')
