from ninja_extra import api_controller, http_get, http_post, NinjaExtraAPI
from typing import Dict
from .schemas import *
from playwright.sync_api import sync_playwright
import json
import time 
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests

api = NinjaExtraAPI(urls_namespace='Test')

def login(page, email, password):
    email_selector = 'input[name="email"]'
    password_selector = 'input[name="credentials.passcode"]'
    time.sleep(random.uniform(1, 3)) 
    for char in email:
        page.type(email_selector, char)
        time.sleep(random.uniform(0.1, 0.3)) 
    print("Email Entered")
    page.wait_for_load_state("load")
    emailbutton = 'button[type="submit"]'
    time.sleep(random.uniform(1, 3)) 
    page.click(emailbutton)
    time.sleep(3)  
    for char in password:
        page.type(password_selector, char)
        time.sleep(random.uniform(0.1, 0.3))
    print("Password Entered") 
    passbutton = 'input[type="submit"]'
    time.sleep(random.uniform(1, 3)) 
    page.click(passbutton)
    
def getLocationNames(page):
    buttonDiv = page.query_selector('button[class*="icon__touchable___KbPwcx9Lf7vYSzlRcriNs Nav__restaurantName___nVhB83U8682y5H2n2xxh1"]')
    if not buttonDiv:
        print("Button Div Not Found")
        return False
    buttonDiv.click()
    time.sleep(3)
    
    changeBtn = page.query_selector('button[data-testid="switchNavButton"]')
    if not changeBtn:
        print("changeBtn Div Not Found")
        return False
    changeBtn.click()
    time.sleep(2)
    
    locations = []
    locationsDiv = page.query_selector_all('li[class*="ItemList__item__container___Ou2IYFEAeYIkupVtCxW7U"]')
    print(len(locationsDiv))
    for index, location in enumerate(locationsDiv):
        if index == 0:
            continue
        locationNameSelector = location.query_selector('div[class*="ItemList__name___3X1UIhohsFMIfTMD_CtqyO ItemList__left___C2OFFqc0xdMaRI4ewZ3zI"]')
        if locationNameSelector:
            locationName = locationNameSelector.inner_text()
            locations.append(locationName)
    return locations

def extractUsingPlaywright(email, password):
    url = 'https://guestcenter.opentable.com/login'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(url, timeout=3200000)
        print("Logging - in")
        login(page, email, password)
        print("Out-Side log-in")
        time.sleep(random.uniform(7, 12))
        # Checking Login or Not
        errorIcon = page.query_selector('div[class*="okta-form-infobox-error infobox infobox-error"]')
        if errorIcon:
            print("Invalid Credentials")
            return None, "Invalid Credentials", False
        page.goto('https://guestcenter.opentable.com/restaurant/732226/home', timeout=12000)
        page.wait_for_load_state("load")
        time.sleep(random.uniform(5, 9))
        
        locations = getLocationNames(page)
        return locations, None, True
    
def sendDataToWebHook(locations, error, valid):
    if not valid:
        payload = {
            "status": "false",
            "error": error,
            "platform": "opentable"
            
        }
    else:
        formatted_locations = [{'location': loc} for loc in locations]
        locations_json = json.dumps(formatted_locations)
        payload = {
            "status": "true",
            "locations": locations_json,
            "platform": "opentable"
        }
    url = "https://ecom.teaconnect.io/integration_sse"
    response = requests.post(url, json=payload)
    print("PayLoad: " , payload)
    return response

def getLocations(email, password):
    locations, error, valid = extractUsingPlaywright(email, password)
    response = sendDataToWebHook(locations, error, valid)
    return response

def run_in_executor(func, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.to_thread(func, *args))
    loop.close()

@api_controller("", tags=["Test"])
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
        print("Email: ", email)
        print("Password: ", password)
    
        executor = ThreadPoolExecutor()
        executor.submit(run_in_executor, getLocations, email, password)

        return 200, {
            "message": "Success",
        }

api.register_controllers(Locations)
