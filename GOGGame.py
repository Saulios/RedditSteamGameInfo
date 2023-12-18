import json
import time

import re
import requests
import dateutil.parser
from dateutil.parser import ParserError
from bs4 import BeautifulSoup

from SteamGame import SteamGame
from SteamSearchGame import SteamSearchGame


class GOGGame:

    def __init__(self, game_name, gog_link):
        self.url = "https://catalog.gog.com/v1/catalog?productType=in:game,pack,dlc,extras&query=like:" + game_name
        while True:
            try:
                url_json = requests.get(self.url, timeout=15)
                break
            except requests.exceptions.RequestException:
                print("GOG request timeout: sleep for 15 seconds and try again")
                time.sleep(15)
        if 'json' in url_json.headers.get('Content-Type') and len(url_json.content) != 0:
            self.json = json.loads(url_json.content.decode('utf-8-sig'))
        else:
            return None

        self.product = self.getproduct(game_name, gog_link)
        if self.product is None:
            return None

        if gog_link == "":
            # get link from catalog if submission is without gog link
            gog_link = self.product['slug'].replace("-", "_")

        self.gog_link = gog_link
        self.title = self.title()
        self.gettype = self.gettype()
        self.features = self.getfeatures()
        self.genres_tags = self.genres_tags(self.genres(), self.tags())
        self.releasedate = self.releasedate()
        self.reviewsummary = self.reviewsummary()
        self.reviewdetails = self.reviewdetails(gog_link)
        self.developers = self.developers()
        self.os = self.os()
        self.steamgame = self.steamgame(game_name)
        self.blurb = self.steamreviews = self.pcgamingwiki = None
        if self.steamgame.appid != 0:
            self.blurb, self.steamreviews = self.steamgame_info(self.steamgame.appid)
            self.pcgamingwiki = SteamGame.pcgamingwiki(self, self.steamgame.appid)

    def getproduct(self, game_name, gog_link):
        game_name_lowercase = re.sub(r'[\W_]+', u' ', game_name, flags=re.UNICODE).lower()
        if 'products' in self.json:
            for product in self.json['products']:
                if product['slug'].replace("-", " ") == gog_link.replace("-", " "):
                    return product
                title_lowercase = re.sub(r'[\W_]+', u' ', product['title'], flags=re.UNICODE).lower()
                if title_lowercase == game_name_lowercase:
                    return product
        return None

    def title(self):
        return self.product["title"]

    def gettype(self):
        return self.product["productType"]

    def getfeatures(self):
        features = []
        if "features" in self.product:
            for feat in self.product["features"]:
                features.append(feat["name"])
        return features

    def genres(self):
        genres = []
        if "genres" in self.product:
            if len(self.product["genres"]) < 3:
                length = len(genres)
            else:
                length = 3
            for genre in self.product["genres"][0:length]:
                genres.append(genre["name"])
        return genres

    def tags(self):
        tags = []
        if "tags" in self.product:
            for tag in self.product["tags"]:
                tags.append(tag["name"])
        return tags

    def genres_tags(self, genres, tags):
        genres_tags = genres
        tags_count = 0
        for tag in tags:
            if tag not in genres:
                genres_tags.append(tag)
                tags_count += 1
            if tags_count == 6:
                break
        return genres_tags

    def releasedate(self):
        if "releaseDate" in self.product:
            releasedate = self.product["releaseDate"]
            try:
                date_abbr = dateutil.parser.parse(releasedate)
            except (ParserError, TypeError):
                return releasedate
            try:
                date_full = time.strftime('%B %e, %Y', date_abbr.timetuple())
            except TypeError:
                return releasedate
            else:
                return date_full.replace("  ", " ")
        return None

    def reviewsummary(self):
        if "reviewsRating" in self.product:
            if self.product["reviewsRating"] == 0:
                return "No user reviews"
            else:
                return str(self.product["reviewsRating"]/10.0) + " out of 5 stars"
        return None

    def reviewdetails(self, gog_link):
        if "reviewsRating" in self.product:
            if self.product["reviewsRating"] == 0:
                return None
        while True:
            try:
                session = requests.session()
                cookies = {'gog_wantsmaturecontent': '18'}
                gog_page = BeautifulSoup(session.get(
                    "https://www.gog.com/game/" + gog_link,
                    cookies=cookies,
                    timeout=30).text, "html.parser")
                break
            except requests.exceptions.RequestException:
                print("GOG timeout: sleep for 30 seconds and try again")
                time.sleep(30)
        page_script = gog_page.find("script", type="application/ld+json")
        if page_script is not None:
            page_script_json = json.loads(page_script.string)
            if "aggregateRating" in page_script_json and "ratingCount" in page_script_json["aggregateRating"]:
                rating_count = page_script_json["aggregateRating"]["ratingCount"]
            else:
                return None
            if "reviewsRating" in self.product:
                reviewpercentage = self.product["reviewsRating"]*2
            else:
                return None
            if int(rating_count) == 1:
                reviewdetails = " (1 user review)"
            else:
                if reviewpercentage == 100 and int(rating_count) > 2:
                    reviewperc = "All"
                elif reviewpercentage == 100 and int(rating_count) == 2:
                    reviewperc = "Both"
                elif reviewpercentage == 0:
                    reviewperc = "None"
                else:
                    reviewperc = str(reviewpercentage) + "%"
                reviewdetails = " (" + reviewperc + " of the " + rating_count + " user reviews are positive)"
            return reviewdetails
        return None

    def developers(self):
        if "developers" in self.product:
            developers = self.product["developers"]
            devs = []
            for dev in developers:
                devs.append(dev)
            return devs
        return None

    def os(self):
        operating_systems = []
        if "os" in self.product:
            for os in self.product["operatingSystems"]:
                if os == "osx":
                    operating_systems.append("Mac OS X")
                else:
                    operating_systems.append(os.capitalize())
            return operating_systems
        return None

    def steamgame(self, game_name):
        return SteamSearchGame(game_name, False)

    def steamgame_info(self, appid):
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
            steamgame_info_json = json.loads(steam_json.content.decode('utf-8-sig'))
        else:
            # try once more
            try:
                steam_json = requests.get(
                    "https://store.steampowered.com/api/appdetails/?appids=" + appid + "&cc=us",
                    timeout=30)
            except requests.exceptions.RequestException:
                return None, None
            if 'json' in steam_json.headers.get('Content-Type') and len(steam_json.content) != 0:
                self.json = json.loads(steam_json.content.decode('utf-8-sig'))
            else:
                return None, None

        if steamgame_info_json is None or steamgame_info_json[appid]["success"] is not True:
            # appid invalid
            return None, None
        steamgame_info_json = steamgame_info_json[appid]["data"]

        def getDescriptionSnippet():
            snippet = steamgame_info_json["short_description"]

            if snippet is None:
                return ""

            return snippet.strip().replace("*", r"\*")

        def reviews(appid):
            while True:
                try:
                    steam_gamePage = BeautifulSoup(
                        requests.get(
                            'https://store.steampowered.com/app/' + appid + "?cc=us",
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
            if steam_gamePage.title is not None and steam_gamePage.title.string == "Welcome to Steam":
                # redirected to Steam homepage
                return None
            review_div = steam_gamePage.find("div", {"class": "user_reviews"})
            details = lowreviews = ""
            total = 0
            if review_div is None:
                review_div = steam_gamePage.find("div", {"id": "userReviews"})
            if review_div is not None:
                review_div_agg = review_div.find("div", {"itemprop": "aggregateRating"})
                reviews_summary = review_div_agg.find("span", {"class": "game_review_summary"})
                if reviews_summary is not None:
                    details = reviews_summary.string
                review_div_count = review_div.find("meta", {"itemprop": "reviewCount"})
                if review_div_count is None or (review_div_count["content"] is not None and int(review_div_count["content"]) < 100):
                    lowreviews, total = SteamGame.lowreviews(self, appid)
                    if total == 0:
                        return details
                details_span = review_div_agg.select('span[class*="responsive_reviewdesc"]')
                details_span = next(iter(details_span), None)
                if details_span is not None:
                    details_strip = details_span.contents[0].strip()
                    if details_strip != "- Need more user reviews to generate a score":
                        details_strip = details_strip.replace("for this game ", "")
                        details_strip = details_strip.replace("- ", " (")
                        details_strip = details_strip.replace("positive.", "positive)")
                        details_strip = details_strip.replace(",", "")
                        details += (str(details_strip))
            lowreviews_details = lowreviews[lowreviews.find("(")-1:lowreviews.find(")")+1]
            if lowreviews != "" and details != lowreviews_details and total > 0:
                return lowreviews
            else:
                return details

        blurb = getDescriptionSnippet()
        reviews = reviews(appid)
        return blurb, reviews
