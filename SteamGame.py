import re

import requests
from bs4 import BeautifulSoup


class SteamGame:

    def __init__(self, appid):
        self.appID = appid
        self.url = 'http://store.steampowered.com/app/' + appid
        self.gamePage = BeautifulSoup(
            requests.get(self.url, cookies={'birthtime': '640584001', 'lastagecheckage': '20-April-1990'}).text,
            "html.parser")

        self.title = self.gamePage.title.string.replace(" on Steam", "")
        self.price = self.getprice()
        self.achievements = self.getachev()
        self.cards = self.getcards()
        self.unreleased = self.isunreleased()

    def getprice(self):
        price = self.gamePage.find("div", class_="price")

        if price is not None:
            return price.string.strip()
        else:
            return "Free"

    def getachev(self):
        achblock = self.gamePage.find("div", id="achievement_block")

        if achblock is not None:
            return re.sub(r"\D", "", achblock.contents[1].string).strip()  # Remove all non numbers
        else:
            return 0

    def getcards(self):
        category_block = self.gamePage.find("div", id="category_block")

        if category_block is None: return 0
        if "Steam Trading Cards" in category_block.text:
            marketurl = 'https://steamcommunity.com/market/search?q=&category_753_Game%5B0%5D=tag_app_' + self.appID + '&category_753_cardborder%5B0%5D=tag_cardborder_0&category_753_item_class%5B0%5D=tag_item_class_2'
            marketpage = BeautifulSoup(requests.get(marketurl).text, "html.parser")
            return marketpage.find("span", id="searchResults_total").string.strip()

        return 0

    def isunreleased(self):
        unreleased = self.gamePage.find("div", class_="game_area_comingsoon")

        if unreleased is None:
            return False
        else:
            return True
