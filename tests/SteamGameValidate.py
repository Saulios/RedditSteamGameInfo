# Made by /u/HeroCC
# Tests SteamGame's capabilities
# If a unit test fails, please check to see if steam is down or the hardcoded variables have changed

import unittest

from SteamGame import SteamGame


class SteamGameValidate(unittest.TestCase):
    game = SteamGame('72850')  # Use Skyrim as our test game

    def test_gamename(self):
        self.assertEqual(self.game.title, "The Elder Scrolls V: Skyrim")

    def test_appid(self):
        self.assertEqual(self.game.appID, '72850')

    def test_achievements(self):
        self.assertEqual(self.game.achievements, '75')

    def test_cards(self):
        self.assertEqual(self.game.cards, '8')


if __name__ == '__main__':
    unittest.main()
