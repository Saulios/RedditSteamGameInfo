# Made by /u/HeroCC

import os
import re

import praw

from SteamGameObject import SteamGame

BLOCKED_USER_FILE = 'blockedusers.txt'  # Will not reply to these people
BLOCKED_SUBS_FILE = 'blockedsubs.txt'  # Will not comment in these subs

BOT_USERNAME = os.getenv('RSGIB_USERNAME', 'SteamGameInfo')

reddit = praw.Reddit(user_agent='SteamGameInfo Bot by /u/HeroCC',
                     client_id=os.getenv('RSGIB_CLIENT_ID'), client_secret=os.getenv('RSGIB_CLIENT_SECRET'),
                     username=BOT_USERNAME, password=os.getenv('RSGIB_PASSWORD'))


def fitscriteria(s):
    if hasbotalreadyreplied(s): return False
    if s.author.name in open(BLOCKED_USER_FILE).read(): return False
    if s.subreddit.display_name in open(BLOCKED_SUBS_FILE).read(): return False

    return True


def hasbotalreadyreplied(s):
    for comment in s.comments:
        if comment.author == BOT_USERNAME: return True

    return False


def buildcommenttext(g):
    commenttext = '[' + g.title + '](' + g.url + ') (' + g.appID + ')\n\n' + \
                  ' * Currently costs ' + g.price + '\n' + \
                  ' * Has ' + str(g.achievements) + ' achievements\n'

    if int(g.cards) > 0:
        commenttext += ' * Has ' + g.cards + ' total cards\n'

    # Begin footer here
    commenttext += '\n***\n'
    commenttext += 'Steam Game Info Bot by /u/HeroCC'

    return commenttext


subreddit = reddit.subreddit('all')
for submission in subreddit.stream.submissions():
    if submission.url.startswith('http://store.steampowered.com/app') or submission.url.startswith('https://store.steampowered.com/app'):
        firstNumber = re.search('\d+', submission.url).group(0)

        if fitscriteria(submission):
            submission.reply(buildcommenttext(SteamGame(firstNumber)))
            print('Commented on post ' + str(submission) + ' after finding game ' + firstNumber)
