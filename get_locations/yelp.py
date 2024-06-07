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
        for char in email:
            page.type(email_selector, char)
            time.sleep(random.uniform(0.1, 0.3))
        print("Email Entered")
        page.click(password_selector)
        time.sleep(random.uniform(2, 6))
        for char in password:
            page.type(password_selector, char)
            time.sleep(random.uniform(0.1, 0.3))
        print("Password Entered")
        
        time.sleep(2)
        page.locator('"Log in"').click()
        print("Login button clicked")
    except Exception as e:
        raise Exception(f"Login failed: {str(e)}")

def getLocationNames(page):
    try:
        time.sleep(random.uniform(5,8))
        page.wait_for_load_state("load")
        buttonDiv = page.query_selector('p[class*=" y-css-y9og9z"]')
        
        if not buttonDiv:
            raise Exception("Button Div Not Found")
        buttonDiv.click()
        time.sleep(3)
        locations = []
        locationsDiv = page.query_selector_all('div[class*="business-info__09f24__xmMju"]')
        for index, location in enumerate(locationsDiv):
            locationNameSelector = location.query_selector('p[class*=" y-css-jf9frv"]')
            if locationNameSelector:
                locationName = locationNameSelector.inner_text()
                locations.append(locationName)
        return locations
    except Exception as e:
        raise Exception(f"Failed to get location names: {str(e)}")

def extractUsingPlaywright(email, password):
    url = 'https://biz.yelp.com/login'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(url, timeout=3200000)
            login(page, email, password)
            print("Waiting For 1 minute.")
            
            time.sleep(random.uniform(60,70))
            page.wait_for_load_state("load")

            # Checking if still on the login page

            # Check for error messages
            error_message = page.query_selector('span[class*="error"]')
            if error_message:
                error_text = error_message.inner_text()
                print("Error message detected:", error_text)
                return None, f"Error on page: {error_text}", False
            current_url = page.url
            print("Current URL after login attempt:", current_url)
            if "login" in current_url.lower():

                page_content = page.content()
                print("Login failed, still on login page. Logging again:")
                time.sleep(200)
                #print(page_content)
                return None, "Login failed, still on login page", False

            print("Logged in successfully, proceeding to extract locations")

            locations = getLocationNames(page)
            print("Locations extracted:", locations)
            return locations, None, True

    except Exception as e:
        print(f"Exception during login or extraction: {str(e)}")
        return None, str(e), False

def sendDataToWebHook(locations, error, valid):
    if not valid:
        payload = {
            "status": "False",
            "error": error,
            "platform": "yelp"
        }
    else:
        formatted_locations = [{'location': loc} for loc in locations]
        locations_json = json.dumps(formatted_locations)
        payload = {
            "status": "True",
            "locations": locations_json,
            "platform": "yelp"
        }
    url = "https://ecom.teaconnect.io/integration/trigger/update"
    response = requests.post(url, json=payload)
    return response

def getLocations(email, password):
    print("Starting location extraction process...")
    locations, error, valid = extractUsingPlaywright(email, password)
    print("Extraction complete. Sending data to webhook...")
    response = sendDataToWebHook(locations, error, valid)
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
    def TestRoute(self, request):
        return 200, {
            "message": "Hello World!",
        }

    @http_post("/locations", response={200: Dict, 400: Dict})
    def TestRoutePost(self, request, data: Test):
        email = data.email
        password = data.password
        print("Email:", email)
        print("Password:", password)

        executor = ThreadPoolExecutor()
        executor.submit(run_in_executor, getLocations, email, password)

        return 200, {
            "message": "Success",
        }

api.register_controllers(Locations)
