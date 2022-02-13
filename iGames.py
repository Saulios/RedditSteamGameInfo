import time
import json

import requests


class iGames:

    def __init__(self, g_id, website):
        self.g_id = g_id
        x_client_key = ""
        if website == "crucial":
            x_client_key = "micron"
        elif website == "igames":
            x_client_key = "igamesgg"
        while True:
            try:
                if x_client_key != "":
                    headers = {"X-Client-Key": x_client_key}
                    igames_json = requests.get("https://api.igsp.io/promotions", headers=headers, timeout=10)
                else:
                    igames_json = requests.get("https://api.igsp.io/promotions", timeout=10)
                break
            except requests.exceptions.RequestException:
                print("iGames API timeout: sleep for 10 seconds and try again")
                time.sleep(10)

        if 'json' in igames_json.headers.get('Content-Type'):
            self.json = json.loads(igames_json.content.decode('utf-8-sig'))
        else:
            return None

        self.key_claimed, self.key_total, self.key_amount = self.key_info(g_id)

    def key_info(self, g_id):
        key_amount = 0
        key_claimed = 0
        key_total = 0
        for giveaway in self.json:
            if str(giveaway['id']) == str(g_id):
                key_claimed = giveaway['numberClaimed']
                key_total = giveaway['numberTotal']
                key_amount = key_total - key_claimed
        return str(key_claimed), str(key_total), str(key_amount)
