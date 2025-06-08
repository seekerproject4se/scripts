from flask import request, jsonify
from datetime import datetime
from parsers import Parser, WebAuthenticator  # Add WebAuthenticator here
import logging
import traceback


def setup_routes(app):
    @app.route('/authenticate', methods=['POST'])
    def authenticate():
        """Authenticate with a website"""
        try:
            data = request.get_json()
            login_url = data.get('login_url')
            username = data.get('username')
            password = data.get('password')
            use_selenium = data.get('use_selenium', False)
            
            if not all([login_url, username, password]):
                return jsonify({'error': 'Missing required fields: login_url, username, password'}), 400
            
            authenticator = WebAuthenticator()
            
            if use_selenium:
                success = authenticator.authenticate_with_selenium(login_url, username, password)
            else:
                success = authenticator.authenticate_with_requests(login_url, username, password)
            
            if success:
                return jsonify({'status': 'success', 'message': 'Authentication successful'}), 200
            else:
                return jsonify({'status': 'failed', 'message': 'Authentication failed'}), 401
                
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/search', methods=['GET'])
    def search():
        urls = request.args.getlist('urls')  # Just processes the URLs you
        """
        Flask endpoint to process URLs and return extracted data.
        """
        try:
            urls = request.args.getlist('urls')
            if not urls:
                return jsonify({"error": "No URLs provided"}), 400

            results = []
            parser = Parser()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            for url in urls:
                if not parser.is_valid_url(url):
                    logging.error(f"Invalid URL: {url}")
                    results.append({"url": url, "error": "Invalid URL"})
                    continue

                try:
                    parser.parse_data(url)
                    parser.save_csv(url)
                    data_serializable = {
                        key: list(values) for key, values in parser.data_manager.card_dict.items()
                    }
                    results.append({
                        "url": url,
                        "data": data_serializable,
                        "summary": {
                            "emails_count": len(data_serializable['Emails']),
                            "names_count": len(data_serializable['Names']),
                            "addresses_count": len(data_serializable['Addresses']),
                            "pdf_links_count": len(data_serializable['PDFLinks']),
                        }
                    })
                except Exception as e:
                    logging.error(f"Error processing URL {url}: {e}\n{traceback.format_exc()}")
                    results.append({"url": url, "error": str(e)})

            return jsonify(results)
        except Exception as e:
            logging.error(f"Error in search endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/crawl', methods=['POST'])
    def crawl_site():
        """Crawl a website with depth for donor data"""
        try:
            data = request.get_json()
            url = data.get('url')
            max_depth = data.get('max_depth', 4)
            keywords = data.get('keywords', [])
            if not url:
                return jsonify({'error': 'Missing required fields: url'}), 400
            parser = Parser()
            parser.crawl_site(
                start_url=url,
                max_depth=max_depth,
                keywords=keywords
            )
            return jsonify({'status': 'success', 'message': 'Crawling started'}), 200
        except Exception as e:
            logging.error(f"Error in crawl_site: {e}")
            return jsonify({'error': str(e)}), 500
