import re
import time
import json

import requests
import country_converter


class AlienwareArena:

    def __init__(self, url, source):
        self.url = url
        while True:
            session = requests.Session()
            try:
                self.giveawayPage = session.get(
                    self.url,
                    timeout=10).text
            except requests.exceptions.RequestException:
                print("Alienware timeout: sleep for 10 seconds before second try")
                time.sleep(10)
            try:
                # for non-global giveaways it will go to login page
                # first time, so request twice to get giveaway page
                self.giveawayPage = session.get(
                    self.url,
                    timeout=10).text
                break
            except requests.exceptions.RequestException:
                print("Alienware timeout: sleep for 10 seconds and try again")
                time.sleep(10)

        self.countrykeys = self.countrykeys()
        if self.countrykeys is None:
            return None
        self.country_with_keys, self.country_without_keys = self.sorted_countries()
        if source == "new":
            self.country_names_with_keys = self.get_country_names(self.country_with_keys)
            self.country_names_without_keys = self.get_country_names(self.country_without_keys)
        self.keys_tier = self.keys_tier()

    def countrykeys(self):
        try:
            raw_data = re.search(r"(var\scountryKeys\s*=\s*(.*))", str(self.giveawayPage)).group(2)
        except AttributeError:
            return None
        try:
            json_data = json.loads(raw_data[:-1])
        except json.decoder.JSONDecodeError:
            return None
        return json_data

    def sorted_countries(self):
        country_with_keys = []
        country_without_keys = []
        for country in self.countrykeys:
            if len(self.countrykeys[country]) == 0:
                country_without_keys.append(country)
            else:
                country_with_keys.append(country)
        return country_with_keys, country_without_keys

    @classmethod
    def get_country_names(cls, country_list):
        country_names = country_converter.convert(names=country_list, to='name_short')
        country_names = [i for i in country_names if i != "not found"]
        country_names.sort()
        return country_names

    def keys_tier(self):
        keys_tier = []
        tier_arp = {2: " (2500 ARP)", 3: " (7000 ARP)", 4: " (12000 ARP)", 5: " (18000 ARP)"}
        if len(self.country_with_keys) != 0:
            for country in self.country_with_keys:
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
                break
        else:
            keys_tier.append(['0', '0'])
        return keys_tier
