import re
import json
import time
import requests

from bs4 import BeautifulSoup


class SteamGame:

    def __init__(self, appid):
        self.appID = appid
        self.url = 'https://store.steampowered.com/app/' + appid + "?cc=us"
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
        self.isearlyaccess = self.isearlyaccess()
        self.unreleasedtext = self.getunreleasedtext()
        self.blurb = self.getDescriptionSnippet()
        self.reviewsummary = self.reviewsummary()
        self.reviewdetails = self.reviewdetails()
        self.genres = self.genres()
        self.usertags = self.usertags()
        self.basegame = self.basegame()
        self.releasedate = self.releasedate()
        self.nsfw = self.nsfw()
        self.plusone = self.plusone()

    def title(self):
        return self.json["name"]

    def gettype(self):
        return self.json["type"]

    def discountamount(self):
        if "price_overview" in self.json and self.json["price_overview"] is not None:
            amount = self.json["price_overview"]["discount_percent"]
            if amount != 0:
                return "-" + str(amount) + "%"
        elif len(self.json["package_groups"]) != 0:
            amount = self.json["package_groups"][0]["subs"][0]["percent_savings_text"]
            amount = amount.strip()
            if amount != "":
                return amount
            else:
                return False
        elif len(self.json["package_groups"]) == 0 and not self.isfree():
            # check bundles
            bundles = self.gamePage.find_all("div", {"class": "game_area_purchase_game"})
            for bundle in bundles:
                title = bundle.find("h1").next_element
                title = title.text.replace("Buy", "").strip()
                if title == self.title:
                    discount = bundle.find("div", {"class": "discount_pct"})
                    if discount is not None:
                        return discount.string.strip()
        return False

    def getprice(self):
        if "price_overview" in self.json and self.json["price_overview"] is not None:
            finalprice = self.json["price_overview"]["final_formatted"]
            fullprice = self.json["price_overview"]["initial_formatted"]
            return finalprice, fullprice
        if self.isfree():
            finalprice = "Free"
            return finalprice, ""
        if len(self.json["package_groups"]) == 0 and not self.isfree():
            # check bundles
            bundles = self.gamePage.find_all("div", {"class": "game_area_purchase_game"})
            for bundle in bundles:
                title = bundle.find("h1").next_element
                title = title.text.replace("Buy", "").strip()
                if title == self.title:
                    price = bundle.find("div", {"class": "game_purchase_price"})
                    if price is None:
                        finalprice = bundle.find("div", {"class": "discount_final_price"})
                        fullprice = bundle.find("div", {"class": "discount_original_price"})
                    if fullprice is None:
                        return finalprice.string.strip(), ""
                    else:
                        return finalprice.string.strip(), fullprice.string.strip()
        finalprice = "No price found"
        return finalprice, ""

    def isfree(self):
        return self.json["is_free"]

    def getasf(self):
        app_id = self.appID
        if (
            len(self.json["package_groups"]) != 0
            and self.json["package_groups"][0]["subs"][0]["is_free_license"]
            and self.json["package_groups"][0]["subs"][0]["can_get_free_license"] == "1"
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
        snippet = self.json["short_description"]

        if snippet is None:
            return ""

        return snippet.strip().replace("*", "\*")

    def islearning(self):
        return self.gamePage.find("div", class_="learning_about") is not None

    def reviewsummary(self):
        review_div = self.gamePage.find("div", {"class": "user_reviews"})
        if review_div is None:
            review_div = self.gamePage.find("div", {"id": "userReviews"})
        review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
        summary = review_div_agg.find("span", {"class": "game_review_summary"})
        if summary is not None:
            return summary.string
        else:
            return "No user reviews"

    def reviewdetails(self):
        review_div = self.gamePage.find("div", {"class": "user_reviews"})
        if review_div is None:
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

    def usertags(self):
        usertags = self.gamePage.find("div", class_="popular_tags")
        usertags_a = usertags.find_all("a", {"class": "app_tag"})
        if len(usertags_a) != 0:
            result_tags = []
            tags_num = 0
            for tag in usertags_a:
                usertag_strip = tag.text.strip()
                if usertag_strip not in self.genres:
                    result_tags.append(usertag_strip)
                    tags_num += 1
                    if tags_num == 5:
                        break
            return ", ".join(result_tags)
        else:
            return False

    def basegame(self):
        if "fullgame" in self.json:
            basegame = self.json["fullgame"]
            appid = basegame["appid"]
            name = basegame["name"]
            basegameurl = 'https://store.steampowered.com/app/' + appid + "?cc=us"
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
                return appid, name

            def basegameisfree():
                return basegame_data["is_free"]

            def basegameprice():
                def discountamount():
                    if "price_overview" in basegame_data and basegame_data["price_overview"] is not None:
                        amount = basegame_data["price_overview"]["discount_percent"]
                        if amount != 0:
                            return "-" + str(amount) + "%"
                    elif len(basegame_data["package_groups"]) != 0:
                        amount = basegame_data["package_groups"][0]["subs"][0]["percent_savings_text"]
                        amount = amount.strip()
                        if amount != "":
                            return amount
                        else:
                            return False
                    elif len(basegame_data["package_groups"]) == 0 and not basegameisfree():
                        # check bundles
                        bundles = basegamePage.find_all("div", {"class": "game_area_purchase_game"})
                        for bundle in bundles:
                            title = bundle.find("h1").next_element
                            title = title.text.replace("Buy", "").strip()
                            if title == name:
                                discount = basegamePage.find("div", {"class": "discount_pct"})
                                if discount is not None:
                                    return discount.string.strip()
                                    break
                    return False
                if "price_overview" in basegame_data and basegame_data["price_overview"] is not None:
                    finalprice = basegame_data["price_overview"]["final_formatted"]
                    fullprice = basegame_data["price_overview"]["initial_formatted"]
                    return finalprice, fullprice, discountamount()
                if basegameisfree():
                    finalprice = "Free"
                    return finalprice, "", False
                if len(basegame_data["package_groups"]) == 0 and not basegameisfree():
                    # check bundles
                    while True:
                        try:
                            basegamePage = BeautifulSoup(
                                requests.get(
                                    basegameurl,
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
                    bundles = basegamePage.find_all("div", {"class": "game_area_purchase_game"})
                    for bundle in bundles:
                        title = bundle.find("h1").next_element
                        title = title.text.replace("Buy", "").strip()
                        if title == name:
                            price = bundle.find("div", {"class": "game_purchase_price"})
                            if price is None:
                                finalprice = basegamePage.find("div", {"class": "discount_final_price"})
                                fullprice = basegamePage.find("div", {"class": "discount_original_price"})
                            if finalprice is not None:
                                if fullprice is None:
                                    return finalprice.string.strip(), "", discountamount()
                                else:
                                    return finalprice.string.strip(), fullprice.string.strip(), discountamount()
                return "No price found", "", False

            finalprice, fullprice, discount = basegameprice()
            free = basegameisfree()
            return appid, name, finalprice, fullprice, free, discount

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
        exceptions = [346290, 863550, 247120, 397720, 272060, 351940, 319830, 8650, 845070, 1515950, 232770, 608990, 769920, 252150, 583950, 584210, 802240]
        if int(self.appID) in exceptions:
            # some apps marked as free still give +1
            return True
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
