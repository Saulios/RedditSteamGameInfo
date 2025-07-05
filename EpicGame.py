import re
import time
import json
from epicstore_api import EpicGamesStoreAPI
from epicstore_api.exc import EGSException
import country_converter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By


class EpicGame:
    api = EpicGamesStoreAPI()

    def __init__(self, game_name):
        self.blacklisted_countries = None
        self.game_name = game_name
        self.keyword = self.clean_game_name(game_name)

        self.checkout_link = self.pc_checkout()
        self.android_checkout, self.ios_checkout = self.mobile_checkout()

    def pc_checkout(self):
        game_data = []
        checkout_link = ""
        while True:
            try:
                game_data = self.api.fetch_store_games(keywords=self.keyword)
                break
            except:
                print("Epic API timeout: sleep for 30 seconds and try again")
                time.sleep(30)

        games = game_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
        process_keyword = re.sub(r'[\W_]+', u' ', self.keyword, flags=re.UNICODE).lower().strip()

        for game in games:
            # Skip Epic Dev Test Account
            if game.get("seller", {}).get("id") == "o-ufmrk5furrrxgsp5tdngefzt5rxdcn":
                continue
            if game.get("price", {}).get("totalPrice", {}).get("discountPrice") != 0:
                continue
            clean_game_name = self.clean_game_name(game["title"]).lower()
            if clean_game_name == process_keyword or clean_game_name == self.game_name.lower():
                self.blacklisted_countries = self.get_blacklisted_countries(game)
                checkout_link = "offers=1-" + game["namespace"] + "-" + game["id"]
                break

        if checkout_link == "":
            # Fallback: Check free games if no game was found
            try:
                free_games_data = self.api.get_free_games()
            except TypeError:
                return ""
            free_games = free_games_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
            for game in free_games:
                clean_game_name = self.clean_game_name(game["title"]).lower()
                if clean_game_name == process_keyword or clean_game_name == self.game_name.lower():
                    self.blacklisted_countries = self.get_blacklisted_countries(game)
                    namespace, game_id = self.find_free_game_promotion(game)
                    if namespace != "" and game_id != "":
                        checkout_link = "offers=1-" + namespace + "-" + game_id
                        break
                    else:
                        return ""

        return checkout_link

    @staticmethod
    def clean_game_name(game_name):
        return re.sub(r'[™®]', '', game_name)

    def get_blacklisted_countries(self, game):
        blacklisted_countries = ""
        if game["customAttributes"]:
            key_to_find = 'com.epicgames.app.blacklist'
            blacklisted_countries_string = next((item['value'] for item in game["customAttributes"] if item['key'] == key_to_find), "")
            if blacklisted_countries_string and blacklisted_countries_string not in ("[]", "{}"):
                country_codes = blacklisted_countries_string.split(",")
                blacklisted_countries = self.get_country_names(country_codes)
        return blacklisted_countries

    @staticmethod
    def get_country_names(country_list):
        country_names = country_converter.convert(names=country_list, to='name_short')
        if country_names == "not found":
            return ""
        if isinstance(country_names, str):
            country_names = country_names.split()
        country_names = [i for i in country_names if i != "not found"]
        country_names.sort()
        return country_names

    def find_free_game_promotion(self, game):
        namespace = ""
        game_id = ""
        if game["customAttributes"]:
            key_to_find = 'com.epicgames.app.productSlug'
            productslug_string = next((item['value'] for item in game["customAttributes"] if item['key'] == key_to_find), "")
            if not productslug_string:
                # If productSlug is not found, check offerMappings
                productslug_string = next((item['pageSlug'] for item in game["offerMappings"]), "")
            if productslug_string and productslug_string != "[]":
                try:
                    product = self.api.get_product(productslug_string)
                except EGSException:
                    return namespace, game_id
                else:
                    for page in product.get("pages", []):
                        if page["data"]["about"]["title"].lower() == self.game_name.lower():
                            namespace = page["offer"]["namespace"]
                            game_id = page["offer"]["id"]
        return namespace, game_id

    @staticmethod
    def selenium_response(urls):
        # Set up Selenium with headless Chrome
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=options)
        responses = []

        for url in urls:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                expected_conditions.presence_of_element_located((By.TAG_NAME, 'pre'))
            )
            body_text = driver.find_element('tag name', 'pre').text
            responses.append(body_text)

        driver.quit()
        return responses

    def mobile_free_game(self, mobile_json):
        data = mobile_json["data"]
        process_keyword = re.sub(r'[\W_]+', u' ', self.keyword, flags=re.UNICODE).lower().strip()
        mobile_checkout = ""

        for offers in data:
            for offer in offers["offers"]:
                clean_game_name = self.clean_game_name(offer["content"]["title"]).lower()
                if clean_game_name == process_keyword or clean_game_name == self.game_name.lower():
                    mobile_checkout = "offers=1-" + offer["sandboxId"] + "-" + offer["offerId"]
                    break
        return mobile_checkout

    def mobile_checkout(self):
        android_api_link = "https://egs-platform-service.store.epicgames.com/api/v2/public/discover/home?count=10&country=GB&locale=en&platform=android&start=0&store=EGS"
        ios_api_link = "https://egs-platform-service.store.epicgames.com/api/v2/public/discover/home?count=10&country=GB&locale=en&platform=ios&start=0&store=EGS"
        android_str, ios_str = self.selenium_response([android_api_link, ios_api_link])
        android_json = json.loads(android_str)
        ios_json = json.loads(ios_str)

        android_checkout_link = self.mobile_free_game(android_json)
        ios_checkout_link = self.mobile_free_game(ios_json)

        return android_checkout_link, ios_checkout_link
