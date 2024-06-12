from ninja_extra import api_controller, http_get, http_post, NinjaExtraAPI
from typing import Dict
from .schemas import Test
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import time
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests

# Initialize the NinjaExtraAPI
api = NinjaExtraAPI(urls_namespace='Yelp')

# Configuration Constants
YELP_LOGIN_URL = 'https://biz.yelp.com/login'
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
WEBHOOK_URL = "https://ecom.teaconnect.io/integration_sse"

def add_stealth(page):
    """Add stealth modifications to the page to bypass bot detection."""
    page.add_init_script("""
    // Pass the Webdriver Test.
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined
    });

    // Pass the Chrome Test.
    window.chrome = {
      runtime: {}
    };

    // Pass the Permissions Test.
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );

    // Pass the Plugins Length Test.
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
    });

    // Pass the Languages Test.
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
    });
    """)

def login(page, email, password):
    print("PAGE URL: ", page.url)
    try:
        email_selector = 'input[name="email"]'
        password_selector = 'input[name="password"]'
        
        time.sleep(random.uniform(2, 6))
        page.click(email_selector)
        for char in email:
            page.type(email_selector, char)
            time.sleep(random.uniform(0.1, 0.3))
        print("Email entered")
        
        page.click(password_selector)
        time.sleep(random.uniform(2, 6))
        for char in password:
            page.type(password_selector, char)
            time.sleep(random.uniform(0.1, 0.3))
        print("Password entered")
        
        time.sleep(2)
        page.locator('"Log in"').click()
        print("Login button clicked")
    except Exception as e:
        print(f"Login failed: {str(e)}")
        raise

def getLocationNames(page):
    """Extracts location names after logging in."""
    try:
        time.sleep(random.uniform(5, 8))
        page.wait_for_load_state("load")
        
        buttonDiv = page.query_selector('p[class*=" y-css-y9og9z"]')
        if not buttonDiv:
            raise Exception("Button Div Not Found")
        buttonDiv.click()
        time.sleep(3)
        
        locations = []
        locationsDiv = page.query_selector_all('div[class*="business-info__09f24__xmMju"]')
        for location in locationsDiv:
            locationNameSelector = location.query_selector('p[class*=" y-css-jf9frv"]')
            if locationNameSelector:
                locationName = locationNameSelector.inner_text()
                locations.append(locationName)
        return locations
    except Exception as e:
        print(f"Failed to get location names: {str(e)}")
        raise

def extractUsingPlaywright(email, password):
    """Uses Playwright to log in and extract location names from Yelp."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=USER_AGENT
            )
            page = context.new_page()
            add_stealth(page)
            page.goto(YELP_LOGIN_URL, timeout=3200000)
            time.sleep(random.uniform(3, 6))
            print(page.url)
            login(page, email, password)
            print("Waiting for 1 minute.")
            
            time.sleep(random.uniform(50, 60))
            page.wait_for_load_state("load")

            error_message = page.query_selector('span[class*="error"]')
            if error_message:
                error_text = error_message.inner_text()
                print(f"Error message detected: {error_text}")
                return None, f"Error on page: {error_text}", False

            current_url = page.url
            print(f"Current URL after login attempt: {current_url}")
            if "login" in current_url.lower():
                page_content = page.content()
                print("Login failed, still on login page.")
                return None, "Login failed, still on login page", False

            print("Logged in successfully, proceeding to extract locations")
            locations = getLocationNames(page)
            print(f"Locations extracted: {locations}")
            return locations, None, True

    except PlaywrightTimeoutError as e:
        print(f"Playwright timeout: {str(e)}")
        return None, str(e), False
    except Exception as e:
        print(f"Exception during login or extraction: {str(e)}")
        return None, str(e), False

def sendDataToWebHook(locations, error, valid):
    """Sends extracted data to a webhook."""
    try:
        if not valid:
            payload = {
                "status": "false",
                "error": error,
                "platform": "yelp"
            }
        else:
            formatted_locations = [{'location': loc} for loc in locations]
            locations_json = json.dumps(formatted_locations)
            payload = {
                "status": "true",
                "locations": locations_json,
                "platform": "yelp"
            }
            print(f"Data sent to webhook: {payload}")
        
        response = requests.post(WEBHOOK_URL, json=payload)
        return response
    except requests.RequestException as e:
        print(f"Failed to send data to webhook: {str(e)}")
        raise

def getLocations(email, password):
    """Main function to get locations and send them to the webhook."""
    print("Starting location extraction process...")
    locations, error, valid = extractUsingPlaywright(email, password)
    print("Extraction complete. Sending data to webhook...")
    response = sendDataToWebHook(locations, error, valid)
    return response

def run_in_executor(func, *args):
    """Runs a function in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.to_thread(func, *args))
    loop.close()

@api_controller("", tags=["Yelp"])
class Locations:
    @http_get("/", response={200: Dict, 400: Dict})
    def TestRoute(self, request):
        return 200, {
            "message": "Hello World!",
        }

    @http_post("/locations", response={200: Dict, 400: Dict})
    def TestRoutePost(self, request, data: Test):
        email = data.email
        password = data.password
        print(f"Received login request for email: {email} and password: {password}")

        executor = ThreadPoolExecutor()
        executor.submit(run_in_executor, getLocations, email, password)

        return 200, {
            "message": "Success",
        }

api.register_controllers(Locations)
