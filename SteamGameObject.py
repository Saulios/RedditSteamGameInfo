import requests
from bs4 import BeautifulSoup

import re


class SteamGame:

    def __init__(self, appid):
        self.appID = appid
        self.url = 'http://store.steampowered.com/app/' + appid
        self.gamePage = BeautifulSoup(requests.get(self.url).text, "html.parser")

        self.title = self.gamePage.title.string.replace(" on Steam", "")
        self.price = self.getprice()
        self.achievements = self.getachev()
        self.hascards = self.hascards()

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

    def hascards(self):
        category_block = self.gamePage.find("div", id="category_block")

        if category_block is None: return False
        if "Steam Trading Cards" in category_block.text: return True
        return False

