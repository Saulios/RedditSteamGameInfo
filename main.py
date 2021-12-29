#!/usr/bin/env python3
# Reddit Steam Game info Bot
# Resolves Steam URLs from submissions, and comments information about them

import os
import re
import threading
import time

import praw
from prawcore.exceptions import PrawcoreException

from SteamGame import SteamGame
from SteamRemovedGame import SteamRemovedGame
from SteamSearchGame import SteamSearchGame

BLOCKED_USER_FILE = 'blockedusers.txt'  # Will not reply to these people
SUBLIST = "FreeGameFindings"

BOT_USERNAME = os.getenv("RSGIB_USERNAME")

STEAM_APPURL_REGEX = "((https?:\/\/)?)(store.steampowered.com(\/agecheck)?\/app\/\d+)"
STEAMDB_APPURL_REGEX = "((https?:\/\/)?)(steamdb.info\/app\/\d+)"
STEAM_TITLE_REGEX = "\[.*(Steam).*\]\s*\(.*(Game|DLC|Beta|Alpha).*\)"


def fitscriteria(s):
    if s.author.name in open(BLOCKED_USER_FILE).read():
        return False
    if hasbotalreadyreplied(s):
        return False
    if not hasbotalreadyreplied(s):
        return True

    return False


def hasbotalreadyreplied(s):
    if type(s).__name__ == "Submission":
        for comment in s.comments:
            if comment.author == BOT_USERNAME:
                return True
    elif type(s).__name__ == "Comment":
        comment = reddit.comment(s.id)
        comment.refresh()
        if comment.author == BOT_USERNAME:
            return True
        submission_title = str(comment.submission.title)
        megathread = submission_title.lower().replace(" ", "").find("megathread")
        if megathread != -1:
            # has not replied, but skip megathreads
            return True
        for reply in comment.replies:
            if reply.author == BOT_USERNAME:
                return True

    return False


def buildcommenttext(g, removed):
    if isinstance(g.title, str):
        commenttext = ''
        if removed is True:
            commenttext += '*Appears to be removed/banned from Steam. This is information from ' + g.date + ':*\n\n'
        commenttext += '**' + g.title + '**'
        if g.nsfw is not False:
            commenttext += ' *(NSFW)*'
        commenttext += '\n\n'
        if g.gettype == "dlc":
            commenttext += '* DLC links: '
        if g.gettype == "music":
            commenttext += '* Soundtrack links: '
        if g.gettype == "mod":
            commenttext += '* Mod links: '
        commenttext += '[Store Page'
        if removed is True:
            commenttext += ' (archived)'
        commenttext += '](' + g.url + ') | '
        if g.gettype == "game" or g.gettype == "mod":
            commenttext += '[Community Hub](https://steamcommunity.com/app/' + g.appID + ') | '
        commenttext += '[SteamDB](https://steamdb.info/app/' + g.appID + ')\n'
        if not g.gettype == "game" and g.basegame is not None:
            commenttext += '* **' + g.basegame[1] + '** links (base game): '
            if removed:
                commenttext += '[Store Page (archived)](' + g.basegame[5]
            else:
                commenttext += '[Store Page](https://store.steampowered.com/app/' + g.basegame[0]
            commenttext += ') | [Community Hub](https://steamcommunity.com/app/' + g.basegame[0] + ') | [SteamDB](https://steamdb.info/app/' + g.basegame[0] + ')\n\n'
        else:
            commenttext += '\n'
        if not g.unreleased:
            commenttext += 'Reviews: ' + g.reviewsummary + g.reviewdetails + '\n\n'
        if g.blurb != "":
            commenttext += '*' + g.blurb + '*\n\n'
        if g.unreleased:
            if g.getunreleasedtext() is None:
                commenttext += " * Isn't released yet\n"
            else:
                commenttext += ' * ' + g.getunreleasedtext() + '\n'
            if g.isearlyaccess():
                commenttext += ' * Is an Early Access Game\n'
            if g.genres is not False:
                commenttext += ' * Genre: ' + g.genres + '\n'
            if g.usertags is not False:
                commenttext += ' * Tags: ' + g.usertags + '\n'
            if g.plusone:
                commenttext += ' * Full game license (no beta testing) will'
            else:
                commenttext += ' * Will not'
            commenttext += ' give +1 game count [^(what is +1?)](https://www.reddit.com/r/FreeGameFindings/wiki/faq#wiki_what_is_.2B1.3F)\n'
        else:
            if not removed:
                commenttext += ' * '
                if g.gettype == "dlc":
                    commenttext += 'DLC '
                if g.gettype == "music":
                    commenttext += 'Soundtrack '
                commenttext += 'Price: ' + g.price
                if not g.isfree() and g.price != ("Free" and "No price found"):
                    commenttext += ' USD'
                    if g.discountamount is not False:
                        commenttext += ' (' + g.discountamount + ')'
                commenttext += '\n'
                if not g.gettype == "game" and g.basegame is not None and len(g.basegame) > 2:
                    commenttext += ' * Game Price: ' + g.basegame[2]
                    if not g.basegame[3] and g.basegame[2] != ("Free" and "No price found"):
                        commenttext += ' USD'
                        if g.basegame[4] is not False:
                            commenttext += ' (' + g.basegame[4] + ')'
                    commenttext += '\n'
            if g.releasedate is not False:
                commenttext += ' * Release date: ' + g.releasedate + '\n'
            if g.isearlyaccess():
                commenttext += ' * Is an Early Access Game\n'
            if g.genres is not False:
                commenttext += ' * Genre: ' + g.genres + '\n'
            if g.usertags is not False:
                commenttext += ' * Tags: ' + g.usertags + '\n'
            if g.isfree() or g.price == "Free":
                commenttext += ' * Can be added to ASF clients with `!addlicense asf '
                if not g.gettype == "game" and g.basegame is not None and len(g.basegame) > 2 and g.basegame[3]:
                    commenttext += "a/" + g.basegame[0] + " "
                commenttext += g.asf[0] + '`\n'
                if g.asf[1] == "sub":
                    commenttext += ' * Can be added in browsers with `javascript:AddFreeLicense(' + g.asf[0].strip("s/") + ')`\n'
            if g.gettype == "game":
                if g.plusone:
                    commenttext += ' * Gives'
                else:
                    commenttext += ' * Does not give'
                commenttext += ' +1 game count [^(what is +1?)](https://www.reddit.com/r/FreeGameFindings/wiki/faq#wiki_what_is_.2B1.3F)\n'
                if int(g.cards) > 0:
                    commenttext += ' * Has ' + g.cards + ' trading cards'
                    if removed:
                        commenttext += ' (non-marketable)'
                    commenttext += '\n'
                if not int(g.cards) > 0:
                    commenttext += ' * Has no trading cards\n'
                if int(g.achievements) != 0:
                    commenttext += ' * Has ' + str(g.achievements) + ' achievements\n'
                if int(g.achievements) == 0:
                    commenttext += ' * Has no achievements\n'
        commenttext += '\n***\n'
        return commenttext


def buildfootertext():
    footertext = "^(I am a bot) Comments? Suggestions? [Let the FGF mods know!](https://www.reddit.com/message/compose?to=%2Fr%2FFreeGameFindings&subject=FGF%20bot) | [Source](https://github.com/Saulios/RedditSteamGameInfo)"

    return footertext


class SubWatch(threading.Thread):
    def run(self):
        print('Started watching subs: ' + SUBLIST)
        subreddit = reddit.subreddit(SUBLIST)
        while True:
            try:
                for submission in subreddit.stream.submissions(skip_existing=True):
                    if (
                        re.search(STEAM_APPURL_REGEX, submission.url)
                        or re.search(STEAMDB_APPURL_REGEX, submission.url)
                    ):
                        appid = re.search('\d+', submission.url).group(0)

                        if fitscriteria(submission):
                            commenttext = buildcommenttext(SteamGame(appid), False)
                            if commenttext is not None:
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding game ' + appid)
                                    submission.reply(commenttext)
                    elif re.search(STEAM_TITLE_REGEX, submission.title, re.IGNORECASE):
                        title_split = re.split(STEAM_TITLE_REGEX, submission.title)
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission):
                            game = SteamSearchGame(game_name, False)
                            appid = game.appid
                            if appid != 0:
                                commenttext = buildcommenttext(SteamGame(appid), False)
                                if commenttext is not None:
                                    commenttext += buildfootertext()
                                    if len(commenttext) < 10000:
                                        print('Commenting on post ' + str(submission) + ' after finding game ' + game_name)
                                        submission.reply(commenttext)
                            else:
                                game = SteamSearchGame(game_name, True)
                                appid = game.appid
                                if appid != 0:
                                    # try for only removed store page
                                    commenttext = buildcommenttext(SteamGame(appid), False)
                                    if commenttext is None:
                                        # not available on Steam
                                        commenttext = buildcommenttext(SteamRemovedGame(appid), True)
                                    if commenttext is not None:
                                        commenttext += buildfootertext()
                                        if len(commenttext) < 10000:
                                            print('Commenting on post ' + str(submission) + ' after finding removed game ' + game_name)
                                            submission.reply(commenttext)
            except PrawcoreException:
                print('Trying to reach Reddit')
                time.sleep(30)


class CommentWatch(threading.Thread):
    def run(self):
        print('Watching all comments on: ' + SUBLIST)
        while True:
            try:
                for comment in reddit.subreddit(SUBLIST).stream.comments(skip_existing=True):
                    test_comment = re.search(STEAM_APPURL_REGEX, comment.body)
                    if test_comment and fitscriteria(comment):
                        games = []
                        urlregex = re.finditer(STEAM_APPURL_REGEX, comment.body)
                        for url in urlregex:
                            games.append(url.group(0))
                        # remove duplicates
                        games = list(dict.fromkeys(games))
                        appids = []
                        commenttext = ""
                        for i in range(len(games)):
                            appid = re.search('\d+', games[i]).group(0)
                            make_comment = buildcommenttext(SteamGame(appid), False)
                            if make_comment is not None:
                                commenttext += make_comment
                                appids.append(appid)
                        if commenttext != "":
                            commenttext += buildfootertext()
                            if len(commenttext) < 10000:
                                print('Replying to comment ' + str(comment) + ' after finding game ' + ', '.join(appids))
                                comment.reply(commenttext)
            except PrawcoreException:
                print('Trying to reach Reddit')
                time.sleep(30)


if __name__ == "__main__":

    reddit = praw.Reddit(
        user_agent='steamstorelinker',
        client_id=os.getenv('RSGIB_CLIENT_ID'),
        client_secret=os.getenv('RSGIB_CLIENT_SECRET'),
        username=BOT_USERNAME,
        password=os.getenv('RSGIB_PASSWORD')
    )

    subwatch = SubWatch()
    commentwatch = CommentWatch()

    subwatch.start()
    commentwatch.start()
