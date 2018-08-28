#!/usr/bin/env python3
# Reddit Steam Game info Bot
# Resolves Steam URLs from submissions, and comments information about them

import os
import re
import threading

import praw

from SteamGame import SteamGame

BLOCKED_USER_FILE = 'blockedusers.txt'  # Will not reply to these people
BLOCKED_SUBS_FILE = 'blockedsubs.txt'  # Will not comment in these subs

BOT_USERNAME = os.getenv('RSGIB_USERNAME', 'SteamGameInfo')

STEAM_APPURL_REGEX = '((https?:\/\/)?)(store.steampowered.com(\/agecheck)?\/app\/\d+)'
SUBLIST = 'all'


def fitscriteria(s):
    if s.author.name in open(BLOCKED_USER_FILE).read(): return False
    if s.subreddit.display_name in open(BLOCKED_SUBS_FILE).read(): return False
    if hasbotalreadyreplied(s): return False

    return True


def hasbotalreadyreplied(s):
    if type(s).__name__ == 'Submission':
        for comment in s.comments:
            if comment.author == BOT_USERNAME: return True
    elif type(s).__name__ == 'Comment':
        comment = reddit.comment(s.id)
        comment.refresh()
        if comment.author == BOT_USERNAME: return True
        for reply in comment.replies:
            if reply.author == BOT_USERNAME: return True

    return False


def buildcommenttext(g):
    commenttext = '[' + g.title + '](' + g.url + ') (' + g.appID + ')\n\n'
    commenttext += g.blurb + '\n\n'
    if g.unreleased:
        if g.getunreleasedtext() is None: commenttext += ' * Isn\'t released yet\n'
        else: commenttext += ' * ' + g.getunreleasedtext() + '\n'
        return commenttext

    commenttext += ' * Currently is ' + g.price + ' USD'
    if g.price != g.getprice(True): commenttext += ' (from ' + g.getprice(True) + ')'
    commenttext += '\n'
    if g.price == "Free" == "0": commenttext += ' * Can be added to ASF with `!addlicense asf ' + g.appID + '`\n'
    if g.discountamount is not False: commenttext += ' * Is currently discounted ' + g.discountamount + '\n'
    if int(g.achievements) is not 0: commenttext += ' * Has ' + str(g.achievements) + ' achievements\n'
    if int(g.cards) > 0: commenttext += ' * Has ' + g.cards + ' total cards\n'

    # Begin footer here
    commenttext += '\n***\n'
    commenttext += "Comments? Complaints? Concerns? [Let me know](https://reddit.com/message/compose?to=%2Fr%2FGameInfoBot)"
    #commenttext += 'I\'m the [Steam Game Info Bot](https://redd.it/66sqdc) | /r/GameInfoBot'

    return commenttext


class SubWatch(threading.Thread):
    def run(self):
        print('Started watching subs: ' + SUBLIST)
        subreddit = reddit.subreddit(SUBLIST)
        for submission in subreddit.stream.submissions():
            if re.search(STEAM_APPURL_REGEX, submission.url):
                appid = re.search('\d+', submission.url).group(0)

                if fitscriteria(submission):
                    print('Commenting on post ' + str(submission) + ' after finding game ' + appid)
                    submission.reply(buildcommenttext(SteamGame(appid)))


class CommentWatch(threading.Thread):
    def run(self):
        print('Watching all comments on: ' + SUBLIST)
        for comment in reddit.subreddit(SUBLIST).stream.comments():
            urlregex = re.search(STEAM_APPURL_REGEX, comment.body)
            if urlregex:
                url = urlregex.group(0)
                appid = re.search('\d+', url).group(0)
                if fitscriteria(comment):
                    print('Replying to comment ' + str(comment) + ' after finding game ' + appid)
                    comment.reply(buildcommenttext(SteamGame(appid)))


if __name__ == "__main__":
    reddit = praw.Reddit(user_agent='SteamGameInfo Bot by /u/HeroCC',
                         client_id=os.getenv('RSGIB_CLIENT_ID'), client_secret=os.getenv('RSGIB_CLIENT_SECRET'),
                         username=BOT_USERNAME, password=os.getenv('RSGIB_PASSWORD'))

    subwatch = SubWatch()
    commentwatch = CommentWatch()

    subwatch.start()
    commentwatch.start()
