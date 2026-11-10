import re
import time
import json
from bs4 import BeautifulSoup

import requests
import country_converter


class AlienwareArena:

    def __init__(self, url, source):
        self.giveawayPage = None
        self.fetch_giveaway_page(url)
        self.countrykeys = self.countrykeys()
        if self.countrykeys is None:
            return
        self.country_with_keys, self.country_without_keys = self.sorted_countries()
        if source == "new":
            self.country_names_with_keys = self.get_country_names(self.country_with_keys)
            self.country_names_without_keys = self.get_country_names(self.country_without_keys)
        self.keys_tier = self.keys_tier()
        self.arp = self.arp_requirement()

    def fetch_giveaway_page(self, url):
        session = requests.Session()
        while True:
            try:
                # First attempt (might redirect to login)
                session.get(url, timeout=10)
                # Second attempt to get actual content
                response = session.get(url, timeout=10)
                self.giveawayPage = response.text
                break
            except requests.exceptions.RequestException:
                print("Alienware timeout: sleep for 10 seconds and try again")
                time.sleep(10)

    def countrykeys(self):
        match = re.search(r'var\s+countryKeys\s*=\s*(\{.*?});', str(self.giveawayPage))
        if not match:
            return None
        raw_data = match.group(1)
        try:
            return json.loads(raw_data)
        except json.decoder.JSONDecodeError:
            return None

    def sorted_countries(self):
        country_with_keys = []
        country_without_keys = []
        for country in self.countrykeys:
            if len(self.countrykeys[country]) == 0:
                country_without_keys.append(country)
            else:
                country_with_keys.append(country)
        return country_with_keys, country_without_keys

    @staticmethod
    def get_country_names(country_list):
        country_names = country_converter.convert(names=country_list, to='name_short')
        if isinstance(country_names, str):
            # Single country gives back a string, convert it to a list for the loop
            country_names = [country_names]
        country_names = [i for i in country_names if i != "not found"]
        country_names.sort()
        return country_names

    def keys_tier(self):
        keys_tier = []
        tier_arp = {2: " (2500 ARP)", 3: " (7000 ARP)", 4: " (12000 ARP)", 5: " (18000 ARP)"}
        if not self.country_with_keys:
            return keys_tier.append(['0', '0'])

        country = self.country_with_keys[0]
        for tier in self.countrykeys[country]:
            if isinstance(tier, int):
                keys = self.countrykeys[country][0]
                keys_tier.append(['0', str(keys)])
            else:
                keys = self.countrykeys[country][tier]
                if int(tier) > 1:
                    for elem in tier_arp:
                        if elem == int(tier):
                            keys_tier.append([str(tier) + tier_arp[elem], str(keys)])
                else:
                    keys_tier.append([str(tier), str(keys)])
        return keys_tier

    def arp_requirement(self):
        bs_giveawaypage = BeautifulSoup(self.giveawayPage, "html.parser")
        arp_box = bs_giveawaypage.find('div', {"id": "arp-confirmation-modal"}).text
        match = re.search(r'(\d+)\s+ARP', arp_box)
        arp = int(match.group(1)) if match else 0
        return arp
