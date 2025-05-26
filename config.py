# filepath: /Users/josephJbrink/Desktop/scripts/config.py

# Example configuration variables
TOR_PROXY = {
    "http": "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050"
}

# Key data patterns for PDF extraction
key_data_patterns = {
    "donation": r"\$\d+(?:,\d{3})*(?:\.\d{2})?",  # Matches monetary amounts like $1,000.00
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Matches email addresses
    "phone": r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",  # Matches phone numbers like (123) 456-7890
    "address": r"\d{1,5}\s\w+(\s\w+)*,\s\w+,\s[A-Z]{2}\s\d{5}",  # Matches addresses like 123 Main St, City, ST 12345
    "name": r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b",  # Matches names like "John Doe" or "John Michael Doe"
}