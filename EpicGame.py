import re
from epicstore_api import EpicGamesStoreAPI
import country_converter


class EpicGame:
    api = EpicGamesStoreAPI()

    def __init__(self, game_name):
        keyword = re.sub(r'[™®]', '', game_name)
        game_data = self.api.fetch_store_games(keywords=keyword)

        games = game_data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements')
        if not games:
            return None

        self.checkout_link = ""

        for game in games:
            # Skip Epic Dev Test Account
            if game["seller"]["id"] == "o-ufmrk5furrrxgsp5tdngefzt5rxdcn":
                continue
            process_keyword = re.sub(r'[\W_]+', u' ', keyword, flags=re.UNICODE).lower().strip()
            if game["title"].lower() == process_keyword or game["title"].lower() == game_name.lower():
                self.blacklisted_countries = self.blacklisted_countries(game)
                self.checkout_link = "https://store.epicgames.com/purchase?offers=1-" + game["namespace"] + "-" + game["id"]
                break

    def blacklisted_countries(self, game):
        blacklisted_countries = ""
        if game["customAttributes"]:
            key_to_find = 'com.epicgames.app.blacklist'
            blacklisted_countries_string = next((item['value'] for item in game["customAttributes"] if item['key'] == key_to_find), None)
            if blacklisted_countries_string is not None and blacklisted_countries_string != "[]":
                blacklisted_countries = self.get_country_names(blacklisted_countries_string.split(","))
        return blacklisted_countries

    def get_country_names(self, country_list):
        country_names = country_converter.convert(names=country_list, to='name_short')
        if isinstance(country_names, str):
            country_names = country_names.split()
        country_names = [i for i in country_names if i != "not found"]
        country_names.sort()
        return country_names
