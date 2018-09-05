import re
import json

import requests
from bs4 import BeautifulSoup


class SteamGame:

    def __init__(self, appid):
        self.appID = appid
        self.url = 'https://store.steampowered.com/app/' + appid
        self.gamePage = BeautifulSoup(
            requests.get(self.url, cookies={'birthtime': '640584001', 'lastagecheckage': '20-April-1990',
                                            'mature_content': '1'}).text,
            "html.parser")
        self.json = json.loads(requests.get("https://store.steampowered.com/api/appdetails/?appids=" + appid + "&cc=us")
                               .text)[appid]["data"]

        self.title = self.gamePage.title.string.replace(" on Steam", "")
        self.discountamount = self.discountamount()
        self.price = self.getprice()
        self.achievements = self.getachev()
        self.cards = self.getcards()
        self.unreleased = self.isunreleased()
        self.blurb = self.getDescriptionSnippet()

    def discountamount(self):
        amount = self.gamePage.find("div", class_="discount_pct")

        if amount is not None:
            return amount.string.strip()
        else:
            return False

    def getprice(self):
        if len(self.json["package_groups"]) is 0:
            return "Free"
        
        return "$" + str(self.json["package_groups"]
                         [0]
                         ["subs"]
                         [0]
                         ["price_in_cents_with_discount"] / 100)

    def isfree(self):
        return self.json["is_free"]

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

        return unreleased is not None

    def isearlyaccess(self):
        return self.gamePage.find("div", class_="early_access_header") is not None

    def getunreleasedtext(self):
        unreleasedMajor = self.gamePage.find("div", class_="game_area_comingsoon")

        if unreleasedMajor is not None:
            return unreleasedMajor.find("h1").string.strip()
        else:
            return None

    def getDescriptionSnippet(self):
        snippet = self.gamePage.find("div", class_="game_description_snippet")
        if snippet is None:
            return ""

        return snippet.string.strip()
