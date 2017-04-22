#!/usr/bin/env python3
# Reddit Steam Game info Bot
# Resolves Steam URLs from submissions, and comments information about them

import os
import re

import praw

from SteamGameObject import SteamGame

BLOCKED_USER_FILE = 'blockedusers.txt'  # Will not reply to these people
BLOCKED_SUBS_FILE = 'blockedsubs.txt'  # Will not comment in these subs

BOT_USERNAME = os.getenv('RSGIB_USERNAME', 'SteamGameInfo')

STEAM_APPURL_REGEX = '(^(https?:\/\/)?)(store.steampowered.com(\/agecheck)?\/app\/\d+)'

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
    commenttext += 'I\'m the [Steam Game Info Bot](https://redd.it/66sqdc) | /r/GameInfoBot'

    return commenttext


def subwatch():
    sublist = 'all'
    print('Started watching subs: ' + sublist)
    subreddit = reddit.subreddit(sublist)
    for submission in subreddit.stream.submissions():
        if re.search(STEAM_APPURL_REGEX, submission.url):
            appid = re.search('\d+', submission.url).group(0)

            if fitscriteria(submission):
                submission.reply(buildcommenttext(SteamGame(appid)))
                print('Commented on post ' + str(submission) + ' after finding game ' + appid)


def mentionwatch():
    print('Started watching mentions...')
    for mention in reddit.inbox.stream.mentions():
        urlregex = re.search(STEAM_APPURL_REGEX, mention.url)
        if urlregex:
            url = urlregex.group(0)
            appid = re.search('\d+', url).group(0)
            if fitscriteria(mention):
                mention.reply(buildcommenttext(SteamGame(appid)))
                print('Replied to mention ' + str(mention) + ' by ' + mention.author.name + ' with appid ' + appid)


if __name__ == "__main__":
    subwatch()
