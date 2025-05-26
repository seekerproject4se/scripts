from flask import request, jsonify
from datetime import datetime
from parsers import Parser  # Import Parser from parsers
import logging
import traceback


def setup_routes(app):
    @app.route('/search', methods=['GET'])
    def search():
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