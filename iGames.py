import os
import time
import json

import requests


class iGames:

    def __init__(self, g_id, website):
        self.g_id = g_id
        api_url = os.getenv("IGAMES_API")
        x_client_key = ""
        if website == "crucial":
            x_client_key = "micron"
        elif website == "igames":
            x_client_key = "igamesgg"
        while True:
            try:
                if x_client_key != "":
                    headers = {"X-Client-Key": x_client_key}
                    igames_json = requests.get(api_url, headers=headers, timeout=10)
                else:
                    igames_json = requests.get(api_url, timeout=10)
                break
            except requests.exceptions.RequestException:
                print("iGames API timeout: sleep for 10 seconds and try again")
                time.sleep(10)

        if 'json' in igames_json.headers.get('Content-Type'):
            try:
                self.json = json.loads(igames_json.content.decode('utf-8-sig'))
            except json.decoder.JSONDecodeError:
                return None
            try:
                self.json[0]
            except KeyError:
                return None
        else:
            return None

        self.key_claimed, self.key_total, self.key_amount, self.gg_app = self.key_info(g_id)

    def key_info(self, g_id):
        key_amount = 0
        key_claimed = 0
        key_total = 0
        for giveaway in self.json:
            if str(giveaway['id']) == str(g_id):
                if 'overrideButtonLabel' in giveaway and str(giveaway['overrideButtonLabel']) == "Download GG":
                    return str(key_claimed), str(key_total), str(key_amount), True
                key_claimed = giveaway['numberClaimed']
                key_total = giveaway['numberTotal']
                key_amount = key_total - key_claimed
        return str(key_claimed), str(key_total), str(key_amount), False
