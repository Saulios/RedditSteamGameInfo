import re
import json
import time

import requests
import dateutil.parser
import dateutil.tz
from dateutil.parser import ParserError
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
        if self.gamePage.title is not None and self.gamePage.title.string == "Welcome to Steam":
            # redirected to Steam homepage
            return None
        while True:
            try:
                steam_json = requests.get(
                    "https://store.steampowered.com/api/appdetails/?appids=" + appid + "&cc=us",
                    timeout=30)
                break
            except requests.exceptions.RequestException:
                print("Steam api timeout: sleep for 30 seconds and try again")
                time.sleep(30)

        if 'json' in steam_json.headers.get('Content-Type') and len(steam_json.content) != 0:
            self.json = json.loads(steam_json.content.decode('utf-8-sig'))
        else:
            # try once more
            try:
                steam_json = requests.get(
                    "https://store.steampowered.com/api/appdetails/?appids=" + appid + "&cc=us",
                    timeout=30)
            except requests.exceptions.RequestException:
                return None
            if 'json' in steam_json.headers.get('Content-Type') and len(steam_json.content) != 0:
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
        self.unreleased = self.isunreleased()
        self.isearlyaccess = self.isearlyaccess()
        self.unreleasedtext = self.getunreleasedtext()
        self.blurb = self.getDescriptionSnippet()
        self.reviewsummary = self.reviewsummary()
        self.reviewdetails, self.lowreviews = self.reviewdetails()
        self.genres = self.genres()
        self.usertags = self.usertags()
        if self.gettype != "game":
            self.basegame = self.basegame()
        self.releasedate = self.releasedate()
        self.nsfw = self.nsfw()
        self.plusone = self.plusone()
        self.developers, self.developers_num = self.developers()
        if self.gettype == "game":
            self.cards = self.getcards()
            self.pcgamingwiki = self.pcgamingwiki(self.appID)

    def title(self):
        return self.json["name"]

    def gettype(self):
        return self.json["type"]

    def discountamount(self):
        if "price_overview" in self.json and self.json["price_overview"] is not None:
            amount = self.json["price_overview"]["discount_percent"]
            if amount != 0:
                discount_end_time = self.gamePage.find("p", {"class": "game_purchase_discount_quantity"})
                discount_countdown = self.gamePage.find("p", {"class": "game_purchase_discount_countdown"})
                amount = "-" + str(amount) + "%"
                if discount_end_time is not None:
                    discount_end_time = discount_end_time.text.strip()
                    discount_end_time = discount_end_time.replace("Some limitations apply. (?)", "").strip()
                    discount_end_time = discount_end_time.replace("Free to keep when you get it before", "").strip()
                    if discount_end_time == "Free to keep when you get it during this limited-time promotion.":
                        return None
                    try:
                        # convert to UTC
                        dateutil_end_time = discount_end_time.replace("@", "")
                        dateutil_end_time = dateutil.parser.parse(dateutil_end_time).replace(tzinfo=dateutil.tz.gettz("America/Los_Angeles"))
                        dateutil_end_time = dateutil_end_time.astimezone(dateutil.tz.UTC)
                    except ParserError:
                        amount += " until " + discount_end_time.replace(".", "") + " PT"
                        return amount
                    try:
                        date_full = time.strftime('%B %e, %H:%M', dateutil_end_time.timetuple())
                        date_full = date_full.replace("  ", " ")
                    except TypeError:
                        amount += " until " + discount_end_time.replace(".", "") + " PT"
                        return amount
                    else:
                        amount += " until " + date_full + " UTC"
                        return amount
                    amount += " until " + discount_end_time.replace(".", "") + " PT"
                if discount_countdown is not None:
                    discount_countdown = discount_countdown.text.strip()
                    if "ends in" in discount_countdown:
                        game_area_purchase = self.gamePage.find("div", {"class": "game_area_purchase_game"})
                        daily_deal_timer = game_area_purchase.find('script').string
                        daily_deal_timer_unix = [int(s) for s in daily_deal_timer.split() if s.isdigit()]
                        if len(daily_deal_timer_unix) == 1:
                            daily_deal_timer_unix = daily_deal_timer_unix[0]
                            try:
                                # convert unix to UTC
                                daily_deal_timer_convert = time.gmtime(daily_deal_timer_unix)
                                daily_deal_timer_convert = time.strftime("%B %e, %H:%M", daily_deal_timer_convert)
                                daily_deal_timer_convert = daily_deal_timer_convert.replace("  ", " ")
                            except TypeError:
                                return amount
                            amount += " until " + daily_deal_timer_convert + " UTC"
                            return amount
                    else:
                        discount_countdown = discount_countdown.split()[-2:]
                    amount += " until " + " ".join(discount_countdown)
                return amount
        elif len(self.json["package_groups"]) != 0:
            amount = self.json["package_groups"][0]["subs"][0]["percent_savings_text"]
            amount = amount.strip()
            if amount != "":
                return amount
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
        finalprice = "No price found"
        if "price_overview" in self.json and self.json["price_overview"] is not None:
            finalprice = self.json["price_overview"]["final_formatted"]
            fullprice = self.json["price_overview"]["initial_formatted"]
            return finalprice, fullprice
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
                    return finalprice.string.strip(), fullprice.string.strip()
        if self.isfree():
            finalprice = "Free"
        return finalprice, ""

    def isfree(self):
        return self.json["is_free"]

    def getasf(self):
        app_id = self.appID
        if len(self.json["package_groups"]) != 0:
            sub_id = 0
            for sub in self.json["package_groups"][0]["subs"]:
                if sub["is_free_license"]:
                    sub_id = sub["packageid"]
                    break
            if sub_id != 0:
                return "s/" + str(sub_id), "sub"
        elif self.isfree():
            while True:
                try:
                    get_subid = requests.get(
                        "https://store.steampowered.com/broadcast/ajaxgetappinfoforcap?appid=" + self.appID,
                        timeout=30)
                    break
                except requests.exceptions.RequestException:
                    print("Steam store timeout: sleep for 30 seconds and try again")
                    time.sleep(30)
            subid_json = get_subid.json()
            if "is_free" in subid_json and subid_json["is_free"]:
                sub_id = subid_json["subid"]
                if sub_id != 0:
                    return "s/" + str(sub_id), "sub"
        return "a/" + str(app_id), "app"

    def getachev(self):
        achblock = self.gamePage.find("div", id="achievement_block")

        if achblock is not None:
            ach_number = re.sub(r"\D", "", achblock.contents[1].string).strip()  # Remove all non numbers
            if ach_number == "":
                return 0
            return ach_number
        return 0

    def getcards(self):
        barter_app_url = 'https://barter.vg/steam/app/' + self.appID + '/json'
        marketurl = 'https://steamcommunity.com/market/search?q=&category_753_Game%5B0%5D=tag_app_' + self.appID + '&category_753_cardborder%5B0%5D=tag_cardborder_0&category_753_item_class%5B0%5D=tag_item_class_2'
        marketable_url = 'https://steamcommunity.com/market/search?q=This+item+can+no+longer+be+bought+or+sold+on+the+Community+Market&category_753_Game%5B0%5D=tag_app_' + self.appID + '&descriptions=1&category_753_cardborder%5B0%5D=tag_cardborder_0&category_753_item_class%5B0%5D=tag_item_class_2'
        while True:
            try:
                barter_app_json = requests.get(barter_app_url, timeout=30).json()
                break
            except requests.exceptions.RequestException:
                print("Barter.vg timeout: sleep for 30 seconds and try again")
                time.sleep(30)
        total = 0
        marketable = True
        if "id" in barter_app_json and barter_app_json["id"] is not None:
            if "cards" in barter_app_json:
                total = barter_app_json["cards"]
                if "cards_marketable" in barter_app_json and barter_app_json["cards_marketable"] != 1:
                    marketable = False
        else:
            while True:
                try:
                    marketpage = BeautifulSoup(requests.get(marketurl, timeout=30).text, "html.parser")
                    break
                except requests.exceptions.RequestException:
                    print("Steam market timeout: sleep for 30 seconds and try again")
                    time.sleep(30)
            total = marketpage.find("span", id="searchResults_total")
            error_message = marketpage.find("div", class_="market_listing_table_message")
            if error_message is not None and "There was an error performing your search" in error_message.text:
                # market error, use steam tag backup
                category_block = self.gamePage.find("div", id="category_block")

                if category_block is None:
                    return 0, 0
                if "Steam Trading Cards" in category_block.text:
                    return 999, 0, marketurl
            if total is not None:
                while True:
                    try:
                        marketable_check = BeautifulSoup(requests.get(marketable_url, timeout=30).text, "html.parser")
                        break
                    except requests.exceptions.RequestException:
                        print("Steam market timeout: sleep for 30 seconds and try again")
                        time.sleep(30)
                nonmarketable = marketable_check.find("span", id="searchResults_total")
                if nonmarketable is not None:
                    if int(nonmarketable.string.strip()) != 0:
                        marketable = False
                total = int(total.string.strip())
                if total == 0:
                    # Get the page again, something might have parsed wrong
                    while True:
                        try:
                            marketpage = BeautifulSoup(requests.get(marketurl, timeout=30).text, "html.parser")
                            break
                        except requests.exceptions.RequestException:
                            print("Steam market timeout: sleep for 30 seconds and try again")
                            time.sleep(30)
                    total = marketpage.find("span", id="searchResults_total")
                    if total is not None:
                        total = int(total.string.strip())
                    else:
                        total = 0
        drops = total//2 + (total % 2 > 0)
        return total, drops, marketurl, marketable

    def isunreleased(self):
        unreleased = self.gamePage.find("div", class_="game_area_comingsoon")

        return unreleased is not None

    def isearlyaccess(self):
        return self.gamePage.find("div", class_="early_access_header") is not None

    def getunreleasedtext(self):
        unreleasedMajor = self.gamePage.find("div", class_="game_area_comingsoon")

        if unreleasedMajor is not None:
            return unreleasedMajor.find("h1").text.strip()
        return None

    def getDescriptionSnippet(self):
        snippet = self.json["short_description"]

        if snippet is None:
            return ""

        return snippet.strip().replace("*", r"\*")

    def islearning(self):
        return self.gamePage.find("div", class_="learning_about") is not None

    def reviewsummary(self):
        review_div = self.gamePage.find("div", {"class": "user_reviews"})
        if review_div is None:
            review_div = self.gamePage.find("div", {"id": "userReviews"})
        if review_div is not None:
            review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
            summary = review_div_agg.find("span", {"class": "game_review_summary"})
            if summary is not None:
                return summary.string
        releasedate = self.releasedate()
        if (
            releasedate == time.strftime("%B %e, %Y", time.localtime())
            or releasedate == time.strftime("%b %e, %Y", time.localtime())
            or releasedate == time.strftime("%B%e, %Y", time.localtime())
            or releasedate == time.strftime("%b%e, %Y", time.localtime())
        ):
            # Skip review text if app released today and has no reviews
            return ""
        else:
            return "No user reviews"

    def lowreviews(self, appid):
        # gives better review text when at low review amounts
        reviews_url = 'https://store.steampowered.com/appreviews/' + appid + '?json=1&filter=summary&review_type=all&purchase_type=all&language=all'
        lowreviews = ""
        total = 0
        while True:
            try:
                appreviews = requests.get(reviews_url, timeout=30)
                break
            except requests.exceptions.RequestException:
                print("Steam store timeout: sleep for 30 seconds and try again")
                time.sleep(30)
        if 'json' in appreviews.headers.get('Content-Type'):
            appreviews_json = json.loads(appreviews.content.decode('utf-8-sig'))
        else:
            # try once more
            try:
                appreviews = requests.get(reviews_url, timeout=30)
            except requests.exceptions.RequestException:
                return lowreviews, total
            if 'json' in appreviews.headers.get('Content-Type'):
                appreviews_json = json.loads(appreviews.content.decode('utf-8-sig'))
            else:
                return lowreviews, total
        if appreviews_json is None or appreviews_json["success"] != 1:
            return lowreviews, total
        positive = appreviews_json["query_summary"]["total_positive"]
        negative = appreviews_json["query_summary"]["total_negative"]
        total = positive + negative
        if total == 0:
            backup_reviews_url = 'https://store.steampowered.com/appreviews/' + appid + '?json=1'
            while True:
                try:
                    appreviews = requests.get(backup_reviews_url, timeout=30)
                    break
                except requests.exceptions.RequestException:
                    print("Steam store timeout: sleep for 30 seconds and try again")
                    time.sleep(30)
            if 'json' in appreviews.headers.get('Content-Type'):
                appreviews_json = json.loads(appreviews.content.decode('utf-8-sig'))
            else:
                return lowreviews, total
            positive = appreviews_json["query_summary"]["total_positive"]
            negative = appreviews_json["query_summary"]["total_negative"]
            total = positive + negative
            if total == 0:
                return lowreviews, total
        percentage = positive / total * 100
        reviewscore = [[80, "Positive"], [70, "Mostly Positive"], [40, "Mixed"], [20, "Mostly Negative"], [0, "Negative"]]
        reviewscore_50 = [[80, "Very Positive"], [70, "Mostly Positive"], [40, "Mixed"], [20, "Mostly Negative"], [0, "Very Negative"]]
        if 1 < total < 10:
            if positive == total and total > 2:
                lowreviews = "All"
            elif positive == total and total == 2:
                lowreviews = "Both"
            elif negative == total:
                lowreviews = "None"
            else:
                lowreviews = str(positive)
            lowreviews += " of the " + str(total) + " user reviews are positive"
        elif total >= 10:
            if total >= 50:
                for score in reviewscore_50:
                    if int(percentage) >= score[0]:
                        lowreviews += score[1]
                        break
            else:
                for score in reviewscore:
                    if int(percentage) >= score[0]:
                        lowreviews += score[1]
                        break
            lowreviews += " (" + str(int(percentage)) + "% of the " + str(total) + " user reviews are positive)"
        elif positive > 0:
            lowreviews = "1 user review (positive)"
        elif negative > 0:
            lowreviews = "1 user review (negative)"
        return lowreviews, total

    def reviewdetails(self):
        review_div = self.gamePage.find("div", {"class": "user_reviews"})
        details = lowreviews = ""
        total = 0
        if review_div is None:
            review_div = self.gamePage.find("div", {"id": "userReviews"})
        if review_div is not None:
            review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
            review_div_count = review_div.find("meta", {"itemprop": "reviewCount"})
            if review_div_count is None or (review_div_count["content"] is not None and int(review_div_count["content"]) < 100):
                lowreviews, total = SteamGame.lowreviews(self, self.appID)
                if total == 0:
                    return details, False
            details_span = review_div_agg.select('span[class*="responsive_reviewdesc"]')
            details = next(iter(details_span), None)
            if details is not None:
                details_strip = details.contents[0].strip()
                if details_strip != "- Need more user reviews to generate a score":
                    details = details_strip.replace("for this game ", "")
                    details = details.replace("- ", " (")
                    details = details.replace("positive.", "positive)")
                    details = details.replace(",", "")
        lowreviews_details = lowreviews[lowreviews.find("(")-1:lowreviews.find(")")+1]
        if lowreviews != "" and details != lowreviews_details and review_div_count is not None and total > 0 and review_div_count["content"] is not None and review_div_count["content"] == str(total):
            # low reviews but all are direct purchases
            return lowreviews, False
        elif lowreviews != "" and details != lowreviews_details and total > 0:
            # low reviews with key activations
            return lowreviews, True
        else:
            return details, False

    def genres(self):
        if "genres" in self.json:
            genres = self.json["genres"]
            length = 2
            genres_result = []
            if len(genres) < 2:
                length = len(genres)
            for genre in genres[0:length]:
                genre_strip = genre["description"].strip()
                genres_result.append(genre_strip)
            return ", ".join(genres_result)
        return False

    def usertags(self):
        usertags = self.gamePage.find("div", class_="popular_tags")
        if usertags is not None:
            usertags_a = usertags.find_all("a", {"class": "app_tag"})
            if len(usertags_a) != 0:
                result_tags = []
                tags_num = 0
                if self.genres is not False:
                    genre_list = self.genres.split(", ")
                    for i in range(len(genre_list)):
                        result_tags.append(genre_list[i])
                        tags_num += 1
                for tag in usertags_a:
                    usertag_strip = tag.text.strip()
                    if not any(usertag_strip in s for s in result_tags):
                        result_tags.append(usertag_strip)
                        tags_num += 1
                        # combine action and adventure tags
                        if set(['Action', 'Adventure']).issubset(result_tags):
                            insert_position = result_tags.index('Action')
                            del result_tags[insert_position]
                            del result_tags[result_tags.index('Adventure')]
                            if 'Action-Adventure' in result_tags:
                                result_tags.remove('Action-Adventure')
                                result_tags.insert(insert_position, 'Action-Adventure')
                                tags_num -= 2
                            else:
                                result_tags.insert(insert_position, "Action-Adventure")
                                tags_num -= 1
                        elif set(['Action', 'Action-Adventure']).issubset(result_tags):
                            insert_position = result_tags.index('Action')
                            del result_tags[insert_position]
                            del result_tags[result_tags.index('Action-Adventure')]
                            result_tags.insert(insert_position, "Action-Adventure")
                            tags_num -= 1
                        elif set(['Adventure', 'Action-Adventure']).issubset(result_tags):
                            insert_position = result_tags.index('Adventure')
                            del result_tags[insert_position]
                            del result_tags[result_tags.index('Action-Adventure')]
                            result_tags.insert(insert_position, "Action-Adventure")
                            tags_num -= 1
                        # filter double information
                        tag_split = usertag_strip.split(" ")
                        if len(tag_split) > 1 and set(tag_split).issubset(result_tags):
                            insert_position = result_tags.index(tag_split[0])
                            del result_tags[insert_position]
                            to_subtract = 1
                            for string in tag_split[1:]:
                                result_tags.remove(string)
                                to_subtract += 1
                            result_tags.remove(usertag_strip)
                            result_tags.insert(insert_position, usertag_strip)
                            tags_num -= to_subtract
                        if 'Early Access' in result_tags and self.isearlyaccess:
                            result_tags.remove('Early Access')
                            tags_num -= 1
                        if 'Free to Play' in result_tags and self.isfree:
                            result_tags.remove('Free to Play')
                            tags_num -= 1
                        if tags_num == 6:
                            break
                return ", ".join(result_tags)
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

            def basegamepcgamingwiki(appid):
                return self.pcgamingwiki(appid)

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
                                return finalprice.string.strip(), fullprice.string.strip(), discountamount()
                return "No price found", "", False

            finalprice, fullprice, discount = basegameprice()
            free = basegameisfree()
            pcgamingwiki = basegamepcgamingwiki(appid)
            return appid, name, finalprice, fullprice, free, discount, pcgamingwiki

    def releasedate(self):
        if "release_date" in self.json:
            date = self.json["release_date"]
            if date["coming_soon"] is False and date["date"] != "":
                release_date = date["date"]
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

    def nsfw(self):
        nsfw = self.gamePage.find("div", class_="mature_content_notice")
        if nsfw is not None:
            return True
        return False

    def plusone(self):
        exceptions_txt = 'plusone_exceptions.txt'
        with open(exceptions_txt) as exceptions:
            for line in exceptions:
                if not line.strip().startswith("#"):
                    if str(self.appID) == line.rstrip():
                        # some apps marked as free still give +1
                        return True
        if (
            not self.islearning()
            and (self.price[1] != "" or not self.isfree())
        ):
            if self.unreleased:
                return True
            elif not (self.price[0] == "Free" and self.discountamount is False):
                return True
        return False

    def pcgamingwiki(self, appid):
        api_url_appid = "https://www.pcgamingwiki.com/api/appid.php?appid=" + appid
        while True:
            try:
                appid_json = requests.get(api_url_appid, allow_redirects=False, timeout=10)
                break
            except requests.exceptions.RequestException:
                print("PCGamingWiki API timeout: sleep for 10 seconds and try again")
                time.sleep(10)
        if appid_json.text == "":
            # page available
            return True
        else:
            return False

    def developers(self):
        if "developers" in self.json:
            developers = self.json["developers"]
            devs = []
            for developer in developers:
                # Filter commas from names, devs are separated by comma
                dev = developer.replace(",", "").strip()
                devs.append(dev)
            count = len(developers)
            return ", ".join(devs), count
        return False
