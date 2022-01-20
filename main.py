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

STEAM_APPURL_REGEX = r"((https?:\/\/)?)(store.steampowered.com(\/agecheck)?\/app\/\d+)"
STEAMDB_APPURL_REGEX = r"((https?:\/\/)?)(steamdb.info\/app\/\d+)"
STEAM_TITLE_REGEX = r"\[.*(Steam).*\]\s*\(.*(Game|DLC|Beta|Alpha).*\)"
INDIEGALA_URL_REGEX = r"((https?:\/\/)?)(freebies.indiegala.com\/)"
INDIEGALA_TITLE_REGEX = r"\[.*(Indiegala).*\]\s*\(.*(Game).*\)"
EPIC_URL_REGEX = r"((https?:\/\/)?)(epicgames.com\/)"
EPIC_TITLE_REGEX = r"\[.*(Epic).*\]\s*\(.*(Game).*\)"


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


def buildcommenttext(g, removed, source):
    if isinstance(g.title, str):
        commenttext = ''
        if source == "Indiegala" or source == "Epic":
            commenttext += '*Game with the same name on Steam:* '
        if removed:
            commenttext += '*Removed/banned from Steam - this is information from ' + g.date + ':*\n\n'
        commenttext += '**' + g.title + '**'
        if g.nsfw:
            commenttext += ' *(NSFW)*'
        commenttext += '\n\n'
        if g.gettype == "dlc":
            commenttext += '* DLC links: '
        elif g.gettype == "music":
            commenttext += '* Soundtrack links: '
        elif g.gettype == "mod":
            commenttext += '* Mod links: '
        commenttext += '[Store Page'
        if removed:
            commenttext += ' (archived)'
        commenttext += ']('
        if not removed:
            commenttext += g.url.replace("?cc=us", "")
        else:
            commenttext += g.url
        commenttext += ') | '
        if g.gettype == "game" or g.gettype == "mod":
            commenttext += '[Community Hub](https://steamcommunity.com/app/' + g.appID + ') | '
        commenttext += '[SteamDB](https://steamdb.info/app/' + g.appID + ')\n'
        if not g.gettype == "game" and g.basegame is not None:
            commenttext += '* Game links (**' + g.basegame[1] + '**): '
            if removed:
                commenttext += '[Store Page (archived)](' + g.basegame[6]
            else:
                commenttext += '[Store Page](https://store.steampowered.com/app/' + g.basegame[0]
            commenttext += ') | [Community Hub](https://steamcommunity.com/app/' + g.basegame[0] + ') | [SteamDB](https://steamdb.info/app/' + g.basegame[0] + ')\n\n'
        else:
            commenttext += '\n'
        if not g.unreleased and (g.reviewsummary != "" or g.reviewdetails != ""):
            commenttext += 'Reviews: '
            if g.reviewsummary == "No user reviews" and g.reviewdetails != "":
                commenttext += g.reviewdetails
            elif g.reviewdetails != "":
                commenttext += g.reviewsummary + g.reviewdetails
            else:
                commenttext += g.reviewsummary
            commenttext += '\n\n'
        if g.blurb != "":
            commenttext += '*' + g.blurb + '*\n\n'
        if g.unreleased:
            if g.unreleasedtext is None:
                commenttext += " * Isn't released yet\n"
            else:
                commenttext += ' * ' + g.unreleasedtext + '\n'
        if not removed and not (g.unreleased and g.price[0] == "No price found"):
            commenttext += ' * '
            if g.price[0] == "Free" and g.basegame is not None and g.basegame[2] == "Free":
                commenttext += 'Game & '
            if g.gettype == "dlc":
                commenttext += 'DLC '
            elif g.gettype == "music":
                commenttext += 'Soundtrack '
            commenttext += 'Price: '
            if g.price[1] != "":
                commenttext += '~~' + g.price[1] + '~~ '
            commenttext += g.price[0]
            if not g.isfree() and g.price[0] != ("Free" and "No price found"):
                commenttext += ' USD'
                if g.discountamount:
                    commenttext += ' (' + g.discountamount + ')'
            commenttext += '\n'
            if not g.gettype == "game" and g.basegame is not None and len(g.basegame) > 2 and (g.price[0] != "Free" or g.basegame[2] != "Free"):
                commenttext += ' * Game Price: '
                if g.basegame[3] != "":
                    commenttext += '~~' + g.basegame[3] + '~~ '
                commenttext += g.basegame[2]
                if not g.basegame[4] and g.basegame[2] != ("Free" and "No price found"):
                    commenttext += ' USD'
                    if g.basegame[5]:
                        commenttext += ' (' + g.basegame[5] + ')'
                commenttext += '\n'
        if not g.unreleased and g.releasedate:
            commenttext += ' * Release Date: ' + g.releasedate + '\n'
        if g.isearlyaccess and g.gettype == "game":
            commenttext += ' * Is an Early Access Game\n'
        if g.usertags and g.usertags != "":
            commenttext += ' * Genre/Tags: ' + g.usertags + '\n'
        elif g.genres:
            commenttext += ' * Genre: ' + g.genres + '\n'
        if g.gettype == "game" and source == "Steam":
            if not g.unreleased:
                if int(g.achievements) != 0:
                    commenttext += ' * Has ' + str(g.achievements) + ' achievements\n'
                if not type(g.cards) == int:
                    if int(g.achievements) == 0:
                        commenttext += ' * Has no achievements\n'
                    commenttext += ' * Has ' + str(g.cards[0]) + ' trading cards (drops ' + str(g.cards[1]) + ')'
                    if not g.cards[3]:
                        commenttext += ' [non-marketable]'
                    if g.cards[3]:
                        commenttext += ' [^(view on Steam Market)](' + g.cards[2] + ')'
                    commenttext += '\n'
                if type(g.cards) == int:
                    commenttext += ' * Has no trading cards'
                    if int(g.achievements) == 0:
                        commenttext += ' or achievements'
                    commenttext += '\n'
            if not g.unreleased and g.plusone:
                commenttext += ' * Gives'
            elif g.unreleased and g.plusone:
                commenttext += ' * Full game license (no beta testing) will give'
            else:
                commenttext += ' * Does not give'
            commenttext += ' +1 game count [^(what is +1?)](https://www.reddit.com/r/FreeGameFindings/wiki/faq#wiki_what_is_.2B1.3F)\n'
        if (g.isfree() or g.price[0] == "Free") and not g.unreleased and source == "Steam":
            commenttext += ' * Can be added to ASF clients with `!addlicense asf '
            if not g.gettype == "game" and g.basegame is not None and len(g.basegame) > 2 and g.basegame[4]:
                commenttext += "a/" + g.basegame[0] + ","
            commenttext += g.asf[0] + '`\n'
            if g.asf[1] == "sub":
                commenttext += ' * Can be added in browsers/mobile with `javascript:AddFreeLicense(' + g.asf[0].strip("s/") + ')`\n'
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
                        source_platform = "Steam"
                        if fitscriteria(submission):
                            commenttext = buildcommenttext(SteamGame(appid), False, source_platform)
                            if commenttext is not None:
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding game ' + appid)
                                    submission.reply(commenttext)
                    elif re.search(STEAM_TITLE_REGEX, submission.title, re.IGNORECASE):
                        title_split = re.split(STEAM_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission):
                            game = SteamSearchGame(game_name, False)
                            appid = game.appid
                            source_platform = "Steam"
                            if appid != 0:
                                commenttext = buildcommenttext(SteamGame(appid), False, source_platform)
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
                                    commenttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                    if commenttext is None:
                                        # not available on Steam
                                        commenttext = buildcommenttext(SteamRemovedGame(appid), True, source_platform)
                                    if commenttext is not None:
                                        commenttext += buildfootertext()
                                        if len(commenttext) < 10000:
                                            print('Commenting on post ' + str(submission) + ' after finding removed game ' + game_name)
                                            submission.reply(commenttext)
                    elif (
                        (indiegala := re.search(INDIEGALA_TITLE_REGEX, submission.title, re.IGNORECASE)
                            and re.search(INDIEGALA_URL_REGEX, submission.url))
                        or (epic := re.search(EPIC_TITLE_REGEX, submission.title, re.IGNORECASE)
                            and re.search(EPIC_URL_REGEX, submission.url))
                    ):
                        if indiegala is not None:
                            title_split = re.split(INDIEGALA_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                            source_platform = "Indiegala"
                        elif epic is not None:
                            title_split = re.split(EPIC_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                            source_platform = "Epic"
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission):
                            game = SteamSearchGame(game_name, False)
                            appid = game.appid
                            if appid != 0:
                                commenttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                if commenttext is not None:
                                    commenttext += buildfootertext()
                                    if len(commenttext) < 10000:
                                        print('Commenting on post ' + str(submission) + ' after finding game ' + game_name)
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
                        source_platform = "Steam"
                        if (
                            (indiegala := re.search(INDIEGALA_TITLE_REGEX, comment.submission.title, re.IGNORECASE)
                                and re.search(INDIEGALA_URL_REGEX, comment.submission.url))
                            or (epic := re.search(EPIC_TITLE_REGEX, comment.submission.title, re.IGNORECASE)
                                and re.search(EPIC_URL_REGEX, comment.submission.url))
                        ):
                            if indiegala is not None:
                                source_platform = "Indiegala_comment"
                            elif epic is not None:
                                source_platform = "Epic_comment"
                        for i in range(len(games)):
                            appid = re.search('\d+', games[i]).group(0)
                            make_comment = buildcommenttext(SteamGame(appid), False, source_platform)
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
