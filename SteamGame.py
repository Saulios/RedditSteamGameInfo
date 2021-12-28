import re
import json
import time
import requests

from bs4 import BeautifulSoup


class SteamGame:

    def __init__(self, appid):
        self.appID = appid
        self.url = 'https://store.steampowered.com/app/' + appid
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
                        timeout=30).text,
                    "html.parser",
                )
                break
            except requests.exceptions.RequestException:
                print("Steam store timeout: sleep for 30 seconds and try again")
                time.sleep(30)
        while True:
            try:
                steam_json = requests.get(
                    "https://store.steampowered.com/api/appdetails/?appids=" + appid + "&cc=us",
                    timeout=30)
                break
            except requests.exceptions.RequestException:
                print("Steam api timeout: sleep for 30 seconds and try again")
                time.sleep(30)

        if 'json' in steam_json.headers.get('Content-Type'):
            self.json = json.loads(steam_json.content.decode('utf-8-sig'))
        else:
            return None

        if self.json is None or self.json[appid]["success"] is not True:
            # appid invalid
            return None
        self.json = self.json[appid]["data"]

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

    def title(self):
        return self.json["name"]

    def gettype(self):
        return self.json["type"]

    def discountamount(self):
        if len(self.json["package_groups"]) != 0:
            amount = self.json["package_groups"][0]["subs"][0]["percent_savings_text"]
            amount = amount.strip()
            if amount != "":
                return amount
            else:
                return False
        else:
            return False

    def getprice(self):
        if len(self.json["package_groups"]) == 0:
            return "Free"

        price = self.json["package_groups"][0]["subs"][0]["price_in_cents_with_discount"] / 100
        if price == 0:
            return "Free"
        elif self.isfree():
            return "Free"
        else:
            return "$" + str(price)

    def isfree(self):
        return self.json["is_free"]

    def getasf(self):
        app_id = self.appID
        if (
            len(self.json["package_groups"]) != 0
            and self.json["package_groups"][0]["subs"][0]["is_free_license"]
        ):
            sub_id = self.json["package_groups"][0]["subs"][0]["packageid"]
            return "s/" + str(sub_id), "sub"
        return "a/" + str(app_id), "app"

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
                    break
                except requests.exceptions.RequestException:
                    print("Steam market timeout: sleep for 30 seconds and try again")
                    time.sleep(30)
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
            return unreleasedMajor.find("h1").text.strip()
        else:
            return None

    def getDescriptionSnippet(self):
        snippet = self.json["short_description"]

        if snippet is None:
            return ""

        return snippet.strip().replace("*", "\*")

    def islearning(self):
        return self.gamePage.find("div", class_="learning_about") is not None

    def reviewsummary(self):
        review_div = self.gamePage.find("div", {"id": "userReviews"})
        review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
        summary = review_div_agg.find("span", {"class": "game_review_summary"})
        if summary is not None:
            return summary.string
        else:
            return "No user reviews"

    def reviewdetails(self):
        review_div = self.gamePage.find("div", {"id": "userReviews"})
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
        if "genres" in self.json:
            genres = self.json["genres"]
            length = 3
            genres_result = []
            if len(genres) < 3:
                length = len(genres)
            for genre in genres[0:length]:
                genre_strip = genre["description"].strip()
                genres_result.append(genre_strip)
            return ", ".join(genres_result)
        else:
            return False

    def basegame(self):
        if "fullgame" in self.json:
            basegame = self.json["fullgame"]
            appid = basegame["appid"]
            while True:
                try:
                    basegame_json = requests.get(
                        "https://store.steampowered.com/api/appdetails/?appids=" + appid + "&cc=us",
                        timeout=30)
                    break
                except requests.exceptions.RequestException:
                    print("Steam api timeout: sleep for 30 seconds and try again")
                    time.sleep(30)

            if 'json' in basegame_json.headers.get('Content-Type'):
                basegame_data = json.loads(basegame_json.content.decode('utf-8-sig'))[appid]["data"]
            else:
                return appid, basegame["name"]

            def basegameisfree():
                return basegame_data["is_free"]

            def basegameprice():
                if len(basegame_data["package_groups"]) == 0:
                    return "Free"

                price = basegame_data["package_groups"][0]["subs"][0]["price_in_cents_with_discount"] / 100
                if price == 0:
                    return "Free"
                elif basegameisfree():
                    return "Free"
                else:
                    return "$" + str(price)

            def discountamount():
                if len(basegame_data["package_groups"]) != 0:
                    amount = basegame_data["package_groups"][0]["subs"][0]["percent_savings_text"]
                    amount = amount.strip()
                    if amount != "":
                        return amount
                    else:
                        return False
                else:
                    return False

            price = basegameprice()
            free = basegameisfree()
            discount = discountamount()
            return appid, basegame["name"], price, free, discount

    def releasedate(self):
        if "release_date" in self.json:
            date = self.json["release_date"]
            if date["coming_soon"] is False and date["date"] != "":
                return date["date"]
            else:
                return False
        else:
            return False

    def nsfw(self):
        nsfw = self.gamePage.find("div", class_="mature_content_notice")
        if nsfw is not None:
            return True
        else:
            return False

    def plusone(self):
        if (
            not self.islearning()
            and not self.isfree()
        ):
            if (
                not self.unreleased
                and not (
                         self.getprice() == "Free"
                         and self.discountamount is False
                        )
            ):
                return True
            if self.unreleased:
                return True
            else:
                return False
        else:
            return False
