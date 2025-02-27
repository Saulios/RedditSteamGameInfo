import re
import json
import calendar
import time

import requests
import dateutil.parser
from dateutil.parser import ParserError
from bs4 import BeautifulSoup
from SteamGame import SteamGame


class SteamRemovedGame:

    def __init__(self, appid):
        self.appID = appid
        while True:
            try:
                archive_json = requests.get(
                    "https://web.archive.org/cdx/search/cdx?url=store.steampowered.com/app/" + appid + "/*&fl=original,timestamp&filter=statuscode:200&output=json",
                    timeout=15)
                break
            except requests.exceptions.RequestException:
                print("Archive.org request timeout: sleep for 15 seconds and try again")
                time.sleep(15)
        if 'json' in archive_json.headers.get('Content-Type'):
            self.json = self.filterjson(archive_json)
        else:
            return None

        if not self.json:
            # invalid, try for old Steam layout
            while True:
                try:
                    archive_json = requests.get(
                        "https://web.archive.org/cdx/search/cdx?url=store.steampowered.com/app/" + appid + "/&fl=original,timestamp&filter=statuscode:200&output=json",
                        timeout=15)
                    break
                except requests.exceptions.RequestException:
                    print("Archive.org request timeout: sleep for 15 seconds and try again")
                    time.sleep(15)
            if 'json' in archive_json.headers.get('Content-Type'):
                self.json = self.filterjson(archive_json)
            else:
                return None
            if not self.json:
                return None
        self.url, self.date = self.urldate()
        while True:
            try:
                self.gamePage = BeautifulSoup(
                    requests.get(
                        self.url,
                        cookies={
                            "birthtime": "640584001",
                            "lastagecheckage": "20-April-1990",
                            "mature_content": "1",
                        },
                        timeout=15).text,
                    "html.parser",
                )
                break
            except requests.exceptions.RequestException:
                print("Archive.org request timeout: sleep for 15 seconds and try again")
                time.sleep(15)

        self.title = self.title()
        self.gettype = self.gettype()
        self.price = self.getprice()
        self.asf = self.getasf()
        self.achievements = SteamGame.getachev(self)
        self.unreleased = SteamGame.isunreleased(self)
        self.isearlyaccess = SteamGame.isearlyaccess(self)
        self.unreleasedtext = SteamGame.getunreleasedtext(self)
        self.blurb = self.getDescriptionSnippet()
        self.reviewsummary = SteamGame.reviewsummary(self)
        self.reviewdetails, self.lowreviews = SteamGame.reviewdetails(self)
        self.steamdbrating = SteamGame.steamdbrating(self)
        self.genres = self.genres()
        self.usertags = SteamGame.usertags(self)
        if self.gettype != "game":
            self.basegame = self.basegame()
        self.releasedate = self.releasedate()
        self.nsfw = SteamGame.nsfw(self)
        self.plusone = False
        self.developers, self.developers_num = self.developers()
        if self.gettype == "game":
            self.cards = SteamGame.getcards(self)
            self.pcgamingwiki = SteamGame.pcgamingwiki(self, self.appID)

    @classmethod
    def filterjson(cls, archive_json):
        archive_json = json.loads(archive_json.text)
        if len(archive_json) > 0:
            del archive_json[0]
            # remove agecheck pages
            archive_json = [entry for entry in archive_json if not re.search("(agecheck)", entry[0])]
            # keep only english pages
            archive_json = [entry for entry in archive_json if not re.search(r"(\?l=)(?!english)", entry[0])]
            return archive_json
        return []

    def urldate(self):
        newest_date = ''
        newest_url = ''
        for entry in self.json:
            if newest_date == '' or entry[1] > newest_date:
                newest_date = entry[1]
                newest_url = entry[0]
        archive_url = "https://web.archive.org/web/" + newest_date + "/" + newest_url
        year = newest_date[0:4]
        month = newest_date[4:6]
        month = calendar.month_name[int(month)]
        day = newest_date[6:8]
        archive_date = month + " " + str(int(day)) + ", " + year
        return archive_url, archive_date

    def title(self):
        title = self.gamePage.title.string.replace(" on Steam", "")
        return re.sub(r"Save\s[0-9]+%\son\s", "", title)

    def gettype(self):
        gettype = "game"
        description = self.gamePage.find("div", {"class": "glance_details"})
        if description is not None:
            if "requires the base game" in description.text:
                gettype = "dlc"
            elif "additional content for" in description.text:
                gettype = "music"
        return gettype

    def getprice(self):
        finalprice = self.gamePage.find("div", {"class": "game_purchase_price"})
        if finalprice is not None:
            finalprice = finalprice.string.strip()
            if finalprice == "Free" or finalprice == "Free to Play":
                finalprice = "Free"
                return finalprice, ""
        finalprice = "No price found"
        return finalprice, ""

    def isfree(self):
        return False

    def getasf(self):
        app_id = self.appID
        return "a/" + str(app_id), "app"

    def getDescriptionSnippet(self):
        snippet = self.gamePage.find("div", class_="game_description_snippet")

        if snippet is None:
            snippet = self.gamePage.find("div", class_="game_area_description")
            get_description = list(snippet.strings)[2].strip()
            if get_description != "":
                return get_description
            return ""
        return snippet.string.strip()

    def genres(self):
        details_blocks = self.gamePage.find_all("div", class_="details_block")
        for block in details_blocks:
            details_a = block.find_all("a")
            genres = []
            if len(details_a) != 0:
                for link in details_a:
                    if "/genre/" in link.get('href'):
                        genres.append(link.text.strip())
                if len(genres) != 0:
                    return ", ".join(genres[:3])
        return False

    def basegame(self):
        if self.gettype != "game":
            description = self.gamePage.find("div", {"class": "glance_details"})
            basegame_link = description.find("a")
            basegame_href = basegame_link.get('href')
            basegame_href = basegame_href.split("/")
            app = basegame_href.index("app") + 1
            appid = basegame_href[app]

            while True:
                try:
                    basegame_json = requests.get(
                        "https://web.archive.org/cdx/search/cdx?url=store.steampowered.com/app/" + appid + "/*&fl=original,timestamp&filter=statuscode:200&output=json",
                        timeout=15)
                    break
                except requests.exceptions.RequestException:
                    print("Archive.org request timeout: sleep for 15 seconds and try again")
                    time.sleep(15)

            if 'json' in basegame_json.headers.get('Content-Type'):
                basegame_data = self.filterjson(basegame_json)
            else:
                return None
            if not self.json:
                # invalid
                return None

            def basegameurl():
                newest_date = ''
                newest_url = ''
                for entry in basegame_data:
                    if newest_date == '' or entry[1] > newest_date:
                        newest_date = entry[1]
                        newest_url = entry[0]
                archive_url = "https://web.archive.org/web/" + newest_date + "/" + newest_url
                return archive_url

            url = basegameurl()
            while True:
                try:
                    basegamePage = BeautifulSoup(
                        requests.get(
                            url,
                            cookies={
                                "birthtime": "640584001",
                                "lastagecheckage": "20-April-1990",
                                "mature_content": "1",
                            },
                            timeout=15).text,
                        "html.parser",
                    )
                    break
                except requests.exceptions.RequestException:
                    print("Archive.org request timeout: sleep for 15 seconds and try again")
                    time.sleep(15)

            def basegameisfree():
                price = basegamePage.find("div", {"class": "game_purchase_price"})
                if price is not None and "Free" in price.string.strip():
                    return True
                return False

            def basegameprice():
                price = basegamePage.find("div", {"class": "game_purchase_price"})
                if price is None:
                    price = basegamePage.find("div", {"class": "discount_original_price"})
                if price is not None:
                    return price.string.strip()
                return "Free"

            def basegamename():
                title = basegamePage.title.string.replace(" on Steam", "")
                return re.sub(r"Save\s[0-9]+%\son\s", "", title)

            price = basegameprice()
            free = basegameisfree()
            discount = False
            name = basegamename()
            return appid, name, price, "", free, discount, url

    def releasedate(self):
        release_divs = self.gamePage.find_all("div", class_="release_date")
        for div in release_divs:
            if div is not None:
                release_date = div.find("div", {"class": "date"})
                if release_date is None:
                    release_date = div.find("span", {"class": "date"})
                if release_date is not None:
                    try:
                        date_abbr = dateutil.parser.parse(release_date.string)
                    except ParserError:
                        return release_date.string
                    try:
                        date_full = time.strftime('%B %e, %Y', date_abbr.timetuple())
                    except TypeError:
                        return release_date.string
                    else:
                        return date_full.replace("  ", " ")
        details = self.gamePage.find("div", class_="details_block")
        if details is not None:
            release_date = details.find(text=re.compile('Release Date')).next_element.strip()
            try:
                date_abbr = dateutil.parser.parse(release_date)
            except ParserError:
                return release_date
            try:
                date_full = time.strftime('%B %e, %Y', date_abbr.timetuple())
            except TypeError:
                return release_date
            else:
                return date_full.replace("  ", " ")
        return False

    def developers(self):
        developers_div = self.gamePage.find("div", id="developers_list")
        if developers_div is not None:
            count_a = developers_div.find_all("a")
            if count_a is not None:
                count = len(count_a)
            else:
                count = 1
            developers = developers_div.text.strip()
            return developers, count
        return False
