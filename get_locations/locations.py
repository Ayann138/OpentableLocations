from ninja_extra import api_controller, http_get, http_post, NinjaExtraAPI
from typing import Dict
from .schemas import *
from playwright.sync_api import sync_playwright
import os
import json
import time 
import random
api = NinjaExtraAPI(urls_namespace='Test')


def save_session(page, file_path):
    cookies = page.context.cookies()
    with open(file_path, 'w') as f:
        json.dump(cookies, f)

def load_session(context, file_path):
    with open(file_path, 'r') as f:
        cookies = json.load(f)
    context.add_cookies(cookies)

def login(page , email , password):
    email_selector = 'input[name="email"]'
    password_selector = 'input[name="credentials.passcode"]'
    time.sleep(random.uniform(1, 3)) 
    for char in email:
        page.type(email_selector, char)
        time.sleep(random.uniform(0.1,0.3)) 
    page.wait_for_load_state("load")
    emailbutton = 'button[type="submit"]'
    time.sleep(random.uniform(1, 3)) 
    page.click(emailbutton)
    time.sleep(3)  
    for char in password:
        page.type(password_selector, char)
        time.sleep(random.uniform(0.1,0.3)) 
    passbutton = 'input[type="submit"]'
    time.sleep(random.uniform(1, 3)) 
    page.click(passbutton)
    
    
def getLocationNames(page):
    # Find and click the button to open the location menu
    buttonDiv = page.query_selector('button[class*="icon__touchable___KbPwcx9Lf7vYSzlRcriNs Nav__restaurantName___nVhB83U8682y5H2n2xxh1"]')
    if not buttonDiv:
        print("Button Div Not Found")
        return False
    buttonDiv.click()
    time.sleep(3)
    
    # Find and click the switch button to change locations
    changeBtn = page.query_selector('button[data-testid="switchNavButton"]')
    if not changeBtn:
        print("changeBtn Div Not Found")
        return False
    changeBtn.click()
    time.sleep(2)
    
    # Extract location names
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

    

def extractUsingPlaywright(email,password):
    url = 'https://guestcenter.opentable.com/login'
    session_file = 'session.json'
    locations = ['Culture Hospitality']
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        if os.path.exists(session_file):
            load_session(context, session_file)
            page.goto('https://guestcenter.opentable.com/restaurant/732226/home', timeout=32000)
            if not page.url.startswith('https://guestcenter.opentable.com/login'):
                print("Session loaded successfully.")
            else:
                print("Session expired, logging in again.")
                page.goto(url, timeout=3200000)
                login(page,email,password)
                time.sleep(random.uniform(10, 15))
                save_session(page, session_file)
        else:
            page.goto(url, timeout=3200000)
            login(page,email,password)
            time.sleep(random.uniform(7, 12))
            save_session(page, session_file)
        
        #page.goto('https://guestcenter.opentable.com/restaurant/732226/home', timeout=12000)
        page.wait_for_load_state("load")
        time.sleep(random.uniform(5, 9))
        locations = getLocationNames(page)
        return locations
    
def sendDataToWebHook(locations):
    print("Sending Data To WebHook")
    
    
def getLocations(email , password):
    Locations = extractUsingPlaywright(email,password)
    sendDataToWebHook(Locations)
    return Locations
    


@api_controller("", tags=["Test"])
class Locations:
    @http_get("/", response={200: Dict, 400: Dict})        
    def TestRoute(self, request):      
        return 200, {
            "message": "Hello World!", 
        }
        
    @http_post("/add", response={200: Dict, 400: Dict})        
    def TestRoutePost(self, request, data: Test):  
        email = data.email
        password = data.password
        print("Email: " , email)
        print("Password: " , password)  
        locations = getLocations(email , password)     
        return 200, {
            "message": "Hello World!",
            "Locations": locations
        }
    
api.register_controllers(Locations)