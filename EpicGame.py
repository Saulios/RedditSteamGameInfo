import re
import time
from epicstore_api import EpicGamesStoreAPI
from epicstore_api.exc import EGSException
import country_converter


class EpicGame:
    api = EpicGamesStoreAPI()

    def __init__(self, game_name):
        keyword = self.clean_game_name(game_name)
        while True:
            try:
                game_data = self.api.fetch_store_games(keywords=keyword)
            except:
                print("Epic API timeout: sleep for 30 seconds and try again")
                time.sleep(30)

        games = game_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
        process_keyword = re.sub(r'[\W_]+', u' ', keyword, flags=re.UNICODE).lower().strip()
        self.checkout_link = ""

        for game in games:
            # Skip Epic Dev Test Account
            if game["seller"]["id"] == "o-ufmrk5furrrxgsp5tdngefzt5rxdcn":
                continue
            clean_game_name = self.clean_game_name(game["title"]).lower()
            if clean_game_name == process_keyword or clean_game_name == game_name.lower():
                self.blacklisted_countries = self.blacklisted_countries(game)
                self.checkout_link = "https://store.epicgames.com/purchase?offers=1-" + game["namespace"] + "-" + game["id"]
                break

        if self.checkout_link == "":
            # Fallback: Check free games if no game was found
            free_games_data = self.api.get_free_games()
            free_games = free_games_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
            for game in free_games:
                clean_game_name = self.clean_game_name(game["title"]).lower()
                if clean_game_name == process_keyword or clean_game_name == game_name.lower():
                    self.blacklisted_countries = self.blacklisted_countries(game)
                    namespace, id = self.find_free_game_promotion(game, game_name)
                    if namespace != "" and id != "":
                        self.checkout_link = "https://store.epicgames.com/purchase?offers=1-" + namespace + "-" + id
                        break
                    else:
                        return None

        if not games and not free_games:
            return None

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

    def find_free_game_promotion(self, game, game_name):
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
                        if page["data"]["about"]["title"].lower() == game_name.lower():
                            namespace = page["offer"]["namespace"]
                            id = page["offer"]["id"]
        return namespace, id
