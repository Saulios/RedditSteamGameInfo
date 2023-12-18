import time
import re

import requests
from bs4 import BeautifulSoup


class Keyhub:

    def __init__(self, url, source):
        self.url = url.replace("share.", "")
        self.g_id = re.findall(r'\d+', self.url)
        if self.g_id:
            # Get key amount
            self.key_amount = self.key_info()
            if self.key_amount != "0" and source == "new":
                # request page to get steam level requirement
                self.level = self.level_info()
        else:
            return None

    def key_info(self):
        self.giveawaycount_url = "https://api.key-hub.eu/?type=giveawaycount&data=" + self.g_id[0]
        while True:
            try:
                headers = {"Origin": "https://key-hub.eu"}
                self.giveawaycount = requests.get(
                    self.giveawaycount_url,
                    headers=headers,
                    timeout=10).json().get("data")
                break
            except requests.exceptions.RequestException:
                print("Keyhub timeout: sleep for 10 seconds and try again")
                time.sleep(10)
        return str(self.giveawaycount)

    def level_info(self):
        level = 0
        while True:
            try:
                self.giveawayPage = BeautifulSoup(requests.get(
                    self.url,
                    timeout=10).text,
                    "html.parser")
                break
            except requests.exceptions.RequestException:
                print("Keyhub timeout: sleep for 10 seconds and try again")
                time.sleep(10)
        level_span = self.giveawayPage.find("span", class_="friendPlayerLevelNum")
        if level_span is not None:
            level = level_span.text
        return str(level)
