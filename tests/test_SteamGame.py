# Made by /u/HeroCC
# Tests SteamGame's capabilities
# If a unit test fails, please check to see if steam is down or the hardcoded variables have changed

import re
import unittest

from SteamGame import SteamGame
from main import STEAM_APPURL_REGEX


class SteamGameValidate(unittest.TestCase):
    game = SteamGame('72850')  # Use Skyrim as our test game

    def test_regex_normalurl(self):
        self.assertTrue(re.search(STEAM_APPURL_REGEX, 'http://store.steampowered.com/app/489830/'))

    def test_regex_httpsurl(self):
        self.assertTrue(re.search(STEAM_APPURL_REGEX, 'https://store.steampowered.com/app/489830/'))

    def test_regex_agecheck(self):
        self.assertTrue(re.search(STEAM_APPURL_REGEX, 'http://store.steampowered.com/agecheck/app/489830/'))

    def test_regex_stringcontainsurl(self):
        self.assertTrue(re.search(STEAM_APPURL_REGEX, 'Test test http://store.steampowered.com/app/489830/ beep boop'))

    def test_gamename(self):
        self.assertEqual(self.game.title, "The Elder Scrolls V: Skyrim")

    def test_appid(self):
        self.assertEqual(self.game.appID, '72850')

    def test_achievements(self):
        self.assertEqual(self.game.achievements, '75')

    def test_cards(self):
        self.assertEqual(self.game.cards, '8')

    def test_unreleased(self):
        self.assertFalse(self.game.unreleased)


if __name__ == '__main__':
    unittest.main()
