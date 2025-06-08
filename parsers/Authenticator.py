import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from requests_html import HTMLSession

class WebAuthenticator:
    def __init__(self):
        self.session = None
        self.driver = None
        self.cookies_file = "session_cookies.json"
    
    def authenticate_with_requests(self, login_url, username, password, 
                                 username_field="username", password_field="password"):
        """Simple form-based authentication using requests"""
        try:
            self.session = HTMLSession()
            
            # Get login page
            response = self.session.get(login_url)
            response.html.render(timeout=10)
            
            # Prepare login data
            form_data = {
                username_field: username,
                password_field: password
            }
            
            # Submit login
            login_response = self.session.post(login_url, data=form_data)
            
            if login_response.status_code == 200:
                print("✓ Authentication successful")
                self.save_cookies()
                return True
            else:
                print(f"✗ Authentication failed: {login_response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
    
    def authenticate_with_selenium(self, login_url, username, password, 
                                 username_selector="input[name='username']",
                                 password_selector="input[name='password']",
                                 submit_selector="input[type='submit']",
                                 headless=True):
        """Complex authentication using Selenium"""
        try:
            # Setup Chrome options
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.get(login_url)
            
            # Wait for and fill username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
            )
            username_field.clear()
            username_field.send_keys(username)
            
            # Fill password
            password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.clear()
            password_field.send_keys(password)
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_button.click()
            
            # Wait for redirect or success
            time.sleep(3)  # Give time for login to process
            
            # Check if login was successful (you may need to customize this)
            current_url = self.driver.current_url
            if current_url != login_url:
                print("✓ Selenium authentication successful")
                self.save_selenium_cookies()
                return True
            else:
                print("✗ Selenium authentication may have failed")
                return False
                
        except Exception as e:
            print(f"✗ Selenium authentication error: {e}")
            return False
    
    def save_cookies(self):
        """Save session cookies to file"""
        if self.session:
            cookies = self.session.cookies.get_dict()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"✓ Cookies saved to {self.cookies_file}")
    
    def save_selenium_cookies(self):
        """Save Selenium cookies to file"""
        if self.driver:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"✓ Selenium cookies saved to {self.cookies_file}")
    
    def load_cookies_to_session(self, session):
        """Load saved cookies into a requests session"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                
                # Handle both formats (requests dict and selenium list)
                if isinstance(cookies, dict):
                    session.cookies.update(cookies)
                elif isinstance(cookies, list):
                    for cookie in cookies:
                        session.cookies.set(cookie['name'], cookie['value'])
                
                print("✓ Cookies loaded into session")
                return True
        except Exception as e:
            print(f"✗ Error loading cookies: {e}")
        return False
    
    def get_authenticated_session(self):
        """Return the authenticated session"""
        return self.session
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None