import re
import json
import requests
import time
import calendar

from bs4 import BeautifulSoup


class SteamRemovedGame:

    def __init__(self, appid):
        self.appID = appid

        try:
            archive_json = requests.get(
                "https://web.archive.org/cdx/search/cdx?url=store.steampowered.com/app/" + appid + "/*&fl=original,timestamp&filter=statuscode:200&output=json",
                timeout=30)
        except requests.exceptions.RequestException:
            print('archive request timeout')
            return None
        else:
            if 'json' in archive_json.headers.get('Content-Type'):
                self.json = json.loads(archive_json.text)
            else:
                return None

            if not self.json:
                # invalid
                return None
            self.url, self.date = self.urldate()
            try:
                self.gamePage = BeautifulSoup(
                    requests.get(
                        self.url,
                        cookies={
                            "birthtime": "640584001",
                            "lastagecheckage": "20-April-1990",
                            "mature_content": "1",
                        },
                        timeout=30).text,
                    "html.parser",
                )
            except requests.exceptions.RequestException:
                print('archive request timeout')
                return None
            else:
                self.title = self.title()
                self.gettype = self.gettype()
                self.discountamount = self.discountamount()
                self.price = self.getprice()
                self.asf = self.getasf()
                self.achievements = self.getachev()
                self.cards = self.getcards()
                self.unreleased = self.isunreleased()
                self.blurb = self.getDescriptionSnippet()
                self.reviewsummary = self.reviewsummary()
                self.reviewdetails = self.reviewdetails()
                self.usertags = self.usertags()
                self.genres = self.genres()
                self.basegame = self.basegame()
                self.releasedate = self.releasedate()
                self.nsfw = self.nsfw()
                self.plusone = self.plusone()

    def urldate(self):
        newest_date = ''
        newest_url = ''
        for entry in self.json[1:]:
            # Only english pages
            if not re.search("(\?l=)(?!english)", entry[0]):
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
        type = "game"
        description = self.gamePage.find("div", {"class": "glance_details"})
        if description is not None:
            if "requires the base game" in description.text:
                type = "dlc"
            elif "additional content for" in description.text:
                type = "music"
        return type

    def discountamount(self):
        return False

    def getprice(self):
        price = self.gamePage.find("div", {"class": "game_purchase_price"})
        if price is None:
            price = self.gamePage.find("div", {"class": "discount_original_price"})

        if price is not None:
            return price.string.strip()
        else:
            return "Free"

    def isfree(self):
        return False

    def getasf(self):
        app_id = self.appID
        return "a/" + str(app_id)

    def getachev(self):
        achblock = self.gamePage.find("div", id="achievement_block")

        if achblock is not None:
            ach_number = re.sub(r"\D", "", achblock.contents[1].string).strip()  # Remove all non numbers
            if ach_number == "":
                return 0
            else:
                return ach_number
        else:
            return 0

    def getcards(self):
        category_block = self.gamePage.find("div", id="category_block")

        if category_block is None:
            return 0
        if "Steam Trading Cards" in category_block.text:
            marketurl = 'https://steamcommunity.com/market/search?q=&category_753_Game%5B0%5D=tag_app_' + self.appID + '&category_753_cardborder%5B0%5D=tag_cardborder_0&category_753_item_class%5B0%5D=tag_item_class_2'
            while True:
                try:
                    marketpage = BeautifulSoup(requests.get(marketurl, timeout=30).text, "html.parser")
                except requests.exceptions.RequestException:
                    print("Steam market timeout: sleep for 30 seconds and try again")
                    time.sleep(30)
            total = marketpage.find("span", id="searchResults_total")
            if total is not None:
                return total.string.strip()
            else:
                return 0

        return 0

    def isunreleased(self):
        unreleased = self.gamePage.find("div", class_="game_area_comingsoon")

        return unreleased is not None

    def isearlyaccess(self):
        return self.gamePage.find("div", class_="early_access_header") is not None

    def getunreleasedtext(self):
        unreleasedMajor = self.gamePage.find("div", class_="game_area_comingsoon")

        if unreleasedMajor is not None:
            return unreleasedMajor.find("h1").text.strip()
        else:
            return None

    def getDescriptionSnippet(self):
        snippet = self.gamePage.find("div", class_="game_description_snippet")

        if snippet is None:
            snippet = self.gamePage.find("div", class_="game_area_description")
            get_description = list(snippet.strings)[2].strip()
            if get_description != "":
                return get_description
            else:
                return ""

        return snippet.string.strip()

    def islearning(self):
        return self.gamePage.find("div", class_="learning_about") is not None

    def reviewsummary(self):
        review_div = self.gamePage.find("div", {"class": "user_reviews"})
        review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
        summary = review_div_agg.find("span", {"class": "game_review_summary"})
        if summary is not None:
            return summary.string
        else:
            return "No user reviews"

    def reviewdetails(self):
        review_div = self.gamePage.find("div", {"class": "user_reviews"})
        review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
        details_span = review_div_agg.select('span[class*="responsive_reviewdesc"]')
        details = next(iter(details_span), None)
        if details is not None:
            details_strip = details.contents[0].strip()
            if details_strip != "- Need more user reviews to generate a score":
                details = details_strip.replace("for this game ", "")
                details = details.replace("- ", " (")
                details = details.replace("positive.", "positive)")
                details = details.replace(",", "")
                return details
            else:
                return ""
        else:
            return ""

    def usertags(self):
        usertags = self.gamePage.find("div", class_="popular_tags")
        usertags_a = usertags.find_all("a", {"class": "app_tag"})
        if len(usertags_a) != 0:
            length = 5
            if len(usertags_a) < 5:
                length = len(usertags_a)
            result_tags = []
            for tag in usertags_a[0:length]:
                usertag_strip = tag.text.strip()
                result_tags.append(usertag_strip)
            return ", ".join(result_tags)
        else:
            return False

    def genres(self):
        details = self.gamePage.find("div", class_="details_block")
        details_a = details.find_all("a")
        genres = []
        for link in details_a:
            if "/genre/" in link.get('href'):
                genres.append(link.text.strip())
        if len(genres) != 0:
            return ", ".join(genres[:3])
        else:
            return False

    def basegame(self):
        if self.gettype != "game":
            description = self.gamePage.find("div", {"class": "glance_details"})
            basegame_link = description.find("a")
            basegame_href = basegame_link.get('href')
            basegame_href = basegame_href.split("/")
            app = basegame_href.index("app") + 1
            appid = basegame_href[app]

            try:
                basegame_json = requests.get(
                    "https://web.archive.org/cdx/search/cdx?url=store.steampowered.com/app/" + appid + "/*&fl=original,timestamp&filter=statuscode:200&output=json",
                    timeout=30)
            except requests.exceptions.RequestException:
                print('archive request timeout')
                return None

            if 'json' in basegame_json.headers.get('Content-Type'):
                basegame_data = json.loads(basegame_json.text)
            else:
                return None
            if not self.json:
                # invalid
                return None

            def basegameurl():
                newest_date = ''
                newest_url = ''
                for entry in basegame_data[1:]:
                    # Only english pages
                    if not re.search("(\?l=)(?!english)", entry[0]):
                        if newest_date == '' or entry[1] > newest_date:
                            newest_date = entry[1]
                            newest_url = entry[0]
                archive_url = "https://web.archive.org/web/" + newest_date + "/" + newest_url
                return archive_url

            url = basegameurl()
            try:
                basegamePage = BeautifulSoup(
                    requests.get(
                        url,
                        cookies={
                            "birthtime": "640584001",
                            "lastagecheckage": "20-April-1990",
                            "mature_content": "1",
                        },
                        timeout=30).text,
                    "html.parser",
                )
            except requests.exceptions.RequestException:
                print('archive request timeout')
                return None
            else:
                def basegameisfree():
                    return False

                def basegameprice():
                    price = basegamePage.find("div", {"class": "game_purchase_price"})
                    if price is None:
                        price = basegamePage.find("div", {"class": "discount_original_price"})

                    if price is not None:
                        return price.string.strip()
                    else:
                        return "Free"

                def discountamount():
                    return False

                def basegamename():
                    title = basegamePage.title.string.replace(" on Steam", "")
                    return re.sub(r"Save\s[0-9]+%\son\s", "", title)

                price = basegameprice()
                free = basegameisfree()
                discount = discountamount()
                name = basegamename()
                return appid, name, price, free, discount, url

    def releasedate(self):
        release = self.gamePage.find("div", class_="release_date")
        release_date = release.find("div", {"class": "date"})
        if release_date is None:
            release_date = release.find("span", {"class": "date"})

        return release_date.string

    def nsfw(self):
        nsfw = self.gamePage.find("div", class_="mature_content_notice")
        if nsfw is not None:
            return True
        else:
            return False

    def plusone(self):
        return False
