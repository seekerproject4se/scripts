from flask import Flask, request, jsonify
import subprocess
import os
import json

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/search', methods=['GET'])
def search():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400

    # Sanitize the URL to match the Puppeteer script's directory structure
    def sanitize_url(url):
        without_protocol = url.replace('http://', '').replace('https://', '')
        without_trailing_slash = without_protocol.rstrip('/')
        return without_trailing_slash.replace('/', '_').replace(':', '_').replace('.', '_')

    sanitized_url = sanitize_url(url)
    data_dir = os.path.join('data', sanitized_url)
    data_file = os.path.join(data_dir, 'extracted_data.json')

    # Run the Puppeteer script
    try:
        subprocess.run(['node', 'search_puppeteer.js', url], check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Failed to run Puppeteer script: {str(e)}'}), 500

    # Check if the extracted data file exists
    if not os.path.exists(data_file):
        return jsonify({'error': f'Extracted data file not found: {data_file}'}), 404

    # Read and return the extracted data
    with open(data_file, 'r') as f:
        data = json.load(f)

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
