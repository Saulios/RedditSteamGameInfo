import re
import time
import json
from epicstore_api import EpicGamesStoreAPI
from epicstore_api.exc import EGSException
import country_converter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class EpicGame:
    api = EpicGamesStoreAPI()

    def __init__(self, game_name):
        self.game_name = game_name
        self.keyword = self.clean_game_name(game_name)

        self.checkout_link = self.pc_checkout()
        self.android_checkout, self.ios_checkout = self.mobile_checkout()

    def pc_checkout(self):
        while True:
            try:
                game_data = self.api.fetch_store_games(keywords=self.keyword)
                break
            except:
                print("Epic API timeout: sleep for 30 seconds and try again")
                time.sleep(30)

        games = game_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
        process_keyword = re.sub(r'[\W_]+', u' ', self.keyword, flags=re.UNICODE).lower().strip()
        checkout_link = ""

        for game in games:
            # Skip Epic Dev Test Account
            if game.get("seller", {}).get("id") == "o-ufmrk5furrrxgsp5tdngefzt5rxdcn":
                continue
            if game.get("price", {}).get("totalPrice", {}).get("discountPrice") != 0:
                continue
            clean_game_name = self.clean_game_name(game["title"]).lower()
            if clean_game_name == process_keyword or clean_game_name == self.game_name.lower():
                self.blacklisted_countries = self.blacklisted_countries(game)
                checkout_link = "offers=1-" + game["namespace"] + "-" + game["id"]
                break

        if checkout_link == "":
            # Fallback: Check free games if no game was found
            try:
                free_games_data = self.api.get_free_games()
            except TypeError:
                return None
            free_games = free_games_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
            for game in free_games:
                clean_game_name = self.clean_game_name(game["title"]).lower()
                if clean_game_name == process_keyword or clean_game_name == self.game_name.lower():
                    self.blacklisted_countries = self.blacklisted_countries(game)
                    namespace, id = self.find_free_game_promotion(game)
                    if namespace != "" and id != "":
                        checkout_link = "offers=1-" + namespace + "-" + id
                        break
                    else:
                        return None

        if not games and not free_games:
            return None

        return checkout_link

    def clean_game_name(self, game_name):
        return re.sub(r'[™®]', '', game_name)

    def blacklisted_countries(self, game):
        blacklisted_countries = ""
        if game["customAttributes"]:
            key_to_find = 'com.epicgames.app.blacklist'
            blacklisted_countries_string = next((item['value'] for item in game["customAttributes"] if item['key'] == key_to_find), None)
            if blacklisted_countries_string is not None and blacklisted_countries_string != "[]" and blacklisted_countries_string != "{}":
                blacklisted_countries = self.get_country_names(blacklisted_countries_string.split(","))
        return blacklisted_countries

    def get_country_names(self, country_list):
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
        id = ""
        if game["customAttributes"]:
            key_to_find = 'com.epicgames.app.productSlug'
            productslug_string = next((item['value'] for item in game["customAttributes"] if item['key'] == key_to_find), None)
            if productslug_string is None:
                # If productSlug is not found, check offerMappings
                productslug_string = next((item['pageSlug'] for item in game["offerMappings"]), None)
            if productslug_string is not None and productslug_string != "[]":
                try:
                    product = self.api.get_product(productslug_string)
                except EGSException:
                    return namespace, id
                else:
                    for page in product.get("pages", []):
                        if page["data"]["about"]["title"].lower() == self.game_name.lower():
                            namespace = page["offer"]["namespace"]
                            id = page["offer"]["id"]
        return namespace, id

    def selenium_response(self, urls):
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
            time.sleep(3)  # Wait for JavaScript to load
            body_text = driver.find_element('tag name', 'pre').text
            responses.append(body_text)

        driver.quit()
        return responses

    def mobile_free_game(self, mobile_json):
        data = mobile_json["data"]
        process_keyword = re.sub(r'[\W_]+', u' ', self.keyword, flags=re.UNICODE).lower().strip()
        mobile_checkout = ""

        for offers in data:
            if offers["topicId"] == "mobile-android-free-game" or offers["topicId"] == "mobile-ios-free-game":
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
