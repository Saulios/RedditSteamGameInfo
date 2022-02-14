import re
import time
import json

import requests
import pycountry
from pycountry_convert import country_alpha2_to_continent_code
from countryinfo import CountryInfo


class AlienwareArena:

    def __init__(self, url):
        self.url = url
        while True:
            try:
                session = requests.Session()
                self.giveawayPage = session.get(
                    self.url,
                    timeout=10).text
                # for non-global giveaways it will go to the giveaway page second time
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
        self.country_names_with_keys = self.get_country_names(self.country_with_keys)
        self.country_names_without_keys = self.get_country_names(self.country_without_keys)
        if len(self.country_names_with_keys) > 10 and len(self.country_names_without_keys) > 10:
            self.raw_continents_with_keys, self.raw_continents_with_country = self.get_continents(self.country_with_keys)
            self.raw_continents_without_keys, self.raw_continents_without_country = self.get_continents(self.country_without_keys)
            self.continents_with_keys, self.continents_without_keys = self.duplicate_continents()
        self.keys_level = self.keys_level()

    def countrykeys(self):
        try:
            raw_data = re.search(r"(var\scountryKeys\s*=\s*(.*))", str(self.giveawayPage)).group(2)
        except AttributeError:
            return None
        json_data = json.loads(raw_data[:-1])
        return json_data

    def sorted_countries(self):
        country_with_keys = []
        country_without_keys = []
        for country in self.countrykeys:
            if len(self.countrykeys[country]["normal"]) == 0 and len(self.countrykeys[country]["prestige"]) == 0:
                country_without_keys.append(country)
            else:
                country_with_keys.append(country)
        return country_with_keys, country_without_keys

    @classmethod
    def get_country_names(cls, country_list):
        country_names = []
        skip_list = {"AX", "PM", "SH"}
        for item in country_list:
            if item not in skip_list:
                country = pycountry.countries.get(alpha_2=item)
                if country is not None:
                    if country.name == "Russian Federation":
                        country_names.append("Russia")
                    else:
                        country_names.append(country.name)
        country_names.sort()
        return country_names

    @classmethod
    def get_continents(cls, country_list):
        continents_list = {
            'NA': 'North America',
            'SA': 'South America',
            'AS': 'Asia',
            'OC': 'Oceania',
            'AF': 'Africa',
            'EU': 'Europe'}
        continents = []
        north_america = []
        south_america = []
        asia = []
        oceania = []
        africa = []
        europe = []
        for country in country_list:
            try:
                # Islands lead to messy results, don't include countries with population under 500k
                if CountryInfo(country).population() > 500000:
                    #print(country)
                    continent = continents_list[country_alpha2_to_continent_code(country)]
                    #print(continent)
                    continents.append(continent)
                    if continent == "North America" and len(north_america) == 0:
                        north_america.append(pycountry.countries.get(alpha_2=country).name)
                    elif continent == "South America" and len(south_america) == 0:
                        south_america.append(pycountry.countries.get(alpha_2=country).name)
                    elif continent == "Asia" and len(asia) == 0:
                        asia.append(pycountry.countries.get(alpha_2=country).name)
                    elif continent == "Oceania" and len(oceania) == 0:
                        oceania.append(pycountry.countries.get(alpha_2=country).name)
                    elif continent == "Africa" and len(africa) == 0:
                        africa.append(pycountry.countries.get(alpha_2=country).name)
                    elif continent == "Europe" and len(europe) == 0:
                        country = pycountry.countries.get(alpha_2=country)
                        if country.name == "Russian Federation":
                            europe.append("Russia")
                        else:
                            europe.append(country.name)
            except KeyError:
                continue
        NA_count = continents.count('North America')
        SA_count = continents.count('South America')
        AS_count = continents.count('Asia')
        OC_count = continents.count('Oceania')
        AF_count = continents.count('Africa')
        EU_count = continents.count('Europe')
        continents = list(set(continents))
        continents_with_country = list(set(continents))
        # If only one country, change continent with country
        if NA_count == 1:
            continents_with_country.remove("North America")
            continents_with_country.extend(north_america)
        if SA_count == 1:
            continents_with_country.remove("South America")
            continents_with_country.extend(south_america)
        if AS_count == 1:
            continents_with_country.remove("Asia")
            continents_with_country.extend(asia)
        if OC_count == 1:
            continents_with_country.remove("Oceania")
            continents_with_country.extend(oceania)
        if AF_count == 1:
            continents_with_country.remove("Africa")
            continents_with_country.extend(africa)
        if EU_count == 1:
            continents_with_country.remove("Europe")
            continents_with_country.extend(europe)
        continents.sort()
        continents_with_country.sort()
        return continents, continents_with_country

    def duplicate_continents(self):
        continents_with_keys = []
        continents_without_keys = []
        for nokey_cont in self.raw_continents_without_keys:
            if nokey_cont in self.raw_continents_with_keys:
                continents_without_keys.append(nokey_cont + " (partly)")
            else:
                continents_without_keys.append(nokey_cont)
        for key_cont in self.raw_continents_with_keys:
            if key_cont in self.raw_continents_without_keys:
                continents_with_keys.append(key_cont + " (partly)")
            else:
                continents_with_keys.append(key_cont)
        diff_with_keys = set(self.raw_continents_with_keys) - set(self.raw_continents_with_country)
        for diff in diff_with_keys:
            continents_with_keys.append(diff + " (partly)")
        diff_without_keys = set(self.raw_continents_without_keys) - set(self.raw_continents_without_country)
        for diff in diff_without_keys:
            continents_with_keys.append(diff + " (partly)")
        return continents_with_keys, continents_without_keys

    def keys_level(self):
        keys_level = []
        if len(self.country_with_keys) != 0:
            for country in self.country_with_keys:
                if len(self.countrykeys[country]["normal"]) != 0:
                    for level in self.countrykeys[country]["normal"]:
                        if isinstance(level, int):
                            keys_level.append('0')
                            keys = self.countrykeys[country]["normal"][0]
                            keys_level.append(str(keys))
                        else:
                            keys_level.append(str(level))
                            keys = self.countrykeys[country]["normal"][level]
                            keys_level.append(str(keys))
                elif len(self.countrykeys[country]["normal"]) == 0 and len(self.countrykeys[country]["prestige"]) != 0:
                    for prestige_level in self.countrykeys[country]["prestige"]:
                        keys_level.append(str(prestige_level))
                        keys = self.countrykeys[country]["prestige"][prestige_level]
                        keys_level.append(str(keys))
                break
        else:
            keys_level.append('0')
            keys_level.append('0')
        return keys_level
