from ninja_extra import api_controller, http_get, http_post, NinjaExtraAPI
from typing import Dict
from .schemas import Test
from playwright.sync_api import sync_playwright
import json
import time
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests

api = NinjaExtraAPI(urls_namespace='Yelp')

def login(page, email, password):
    try:
        email_selector = 'input[name="email"]'
        password_selector = 'input[name="password"]'
        
        time.sleep(random.uniform(2, 6))
        page.click(email_selector)
        page.fill(email_selector, email)
        print("Email Entered")
        
        time.sleep(random.uniform(2, 6))
        page.click(password_selector)
        page.fill(password_selector, password)
        print("Password Entered")
        
        time.sleep(2)
        page.click('button[type="submit"]')
        print("Login button clicked")
    except Exception as e:
        raise Exception(f"Login failed: {str(e)}")

def get_location_names(page):
    try:
        time.sleep(random.uniform(5, 8))
        page.wait_for_load_state("load")
        
        button_div = page.query_selector('p[class*=" y-css-y9og9z"]')
        if not button_div:
            raise Exception("Button Div Not Found")
        button_div.click()
        time.sleep(3)
        
        locations = []
        locations_div = page.query_selector_all('div[class*="business-info__09f24__xmMju"]')
        for location in locations_div:
            location_name_selector = location.query_selector('p[class*=" y-css-jf9frv"]')
            if location_name_selector:
                location_name = location_name_selector.inner_text()
                locations.append(location_name)
        return locations
    except Exception as e:
        raise Exception(f"Failed to get location names: {str(e)}")

def extract_using_playwright(email, password):
    url = 'https://biz.yelp.com/login'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # Use headless mode
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},  # Set standard viewport size
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # Set User-Agent
            )
            
            # Stealth mode adjustments
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """)

            page = context.new_page()

            page.goto(url, timeout=3200000)
            login(page, email, password)
            print("Waiting For 1 minute.")
            
            time.sleep(random.uniform(60, 70))
            page.wait_for_load_state("load")

            error_message = page.query_selector('span[class*="error"]')
            if error_message:
                error_text = error_message.inner_text()
                print("Error message detected:", error_text)
                return None, f"Error on page: {error_text}", False
            
            current_url = page.url
            print("Current URL after login attempt:", current_url)
            if "login" in current_url.lower():
                login(page, email, password)  
                print("Waiting For 1 minute.")
                time.sleep(random.uniform(70, 80)) 
                print("Current URL after re-login attempt:", page.url)
                time.sleep(200)
                return None, "Login failed, still on login page", False

            print("Logged in successfully, proceeding to extract locations")
            locations = get_location_names(page)
            print("Locations extracted:", locations)
            return locations, None, True
    except Exception as e:
        print(f"Exception during login or extraction: {str(e)}")
        return None, str(e), False

def send_data_to_webhook(locations, error, valid):
    payload = {
        "status": "False" if not valid else "True",
        "error": error,
        "locations": json.dumps([{'location': loc} for loc in locations]) if valid else None,
        "platform": "yelp"
    }
    url = "https://ecom.teaconnect.io/integration/trigger/update"
    response = requests.post(url, json=payload)
    return response

def get_locations(email, password):
    print("Starting location extraction process...")
    locations, error, valid = extract_using_playwright(email, password)
    print("Extraction complete. Sending data to webhook...")
    response = send_data_to_webhook(locations, error, valid)
    print("Data sent to webhook. Response:", response.status_code, response.text)
    return response

def run_in_executor(func, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.to_thread(func, *args))
    loop.close()

@api_controller("", tags=["Yelp"])
class Locations:
    @http_get("/", response={200: Dict, 400: Dict})
    def test_route(self, request):
        return 200, {
            "message": "Hello World!",
        }

    @http_post("/locations", response={200: Dict, 400: Dict})
    def test_route_post(self, request, data: Test):
        email = data.email
        password = data.password
        print("Email:", email)
        print("Password:", password)

        executor = ThreadPoolExecutor()
        executor.submit(run_in_executor, get_locations, email, password)

        return 200, {
            "message": "Success",
        }

api.register_controllers(Locations)
