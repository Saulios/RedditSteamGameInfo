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
from AlienwareArena import AlienwareArena
from iGames import iGames

BLOCKED_USER_FILE = 'blockedusers.txt'  # Will not reply to these people
SUBLIST = "FreeGameFindings"

BOT_USERNAME = os.getenv("RSGIB_USERNAME")

STEAM_APPURL_REGEX = r"((https?:\/\/)?)(store.steampowered.com(\/agecheck)?\/app\/\d+)"
STEAMDB_APPURL_REGEX = r"((https?:\/\/)?)(steamdb.info\/app\/\d+)"
STEAM_TITLE_REGEX = r"\[.*(Steam).*\]\s*\((Game|DLC|Beta|Alpha)\)"
INDIEGALA_URL_REGEX = r"((https?:\/\/)?)(freebies.indiegala.com\/)"
INDIEGALA_TITLE_REGEX = r"\[.*(Indiegala).*\]\s*\((Game)\)"
EPIC_URL_REGEX = r"((https?:\/\/)?)(epicgames.com\/)"
EPIC_TITLE_REGEX = r"\[.*(Epic).*\]\s*\((Game)\)"
ITCH_URL_REGEX = r"((https?:\/\/)?)(itch.io\/)"
ALIENWARE_URL_REGEX = r"(https?:\/\/)?(\b)?\.?(alienwarearena.com\/\w*)"
STEELSERIES_URL_REGEX = r"((https?:\/\/)?)(games.steelseries.com\/giveaway\/\d+)"
CRUCIAL_URL_REGEX = r"((https?:\/\/)?)(games.crucial.com\/promotions\/\d+)"
IGAMES_URL_REGEX = r"((https?:\/\/)?)(igames.gg\/promotions\/\d+)"


def fitscriteria(s):
    with open(BLOCKED_USER_FILE) as blocked_users:
        if s.author.name in blocked_users.read():
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
        try:
            comment.refresh()
        except praw.exceptions.ClientException:
            try:
                comment.refresh()
            except praw.exceptions.ClientException:
                # ignore comment
                return True
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


def buildcommenttext_awa(g, source):
    commenttext = ''
    if source == "new":
        commenttext += "**Giveaway details**\n\n"
    if isinstance(g.keys_level, list) and len(g.keys_level) > 0 and (g.keys_level[0][1] != '0' or (len(g.keys_level) > 1 and g.keys_level[1][1] != '0')):
        if source == "update" or len(g.keys_level) != 0:
            commenttext += "* Available keys: " + g.keys_total + "\n"
            commenttext += "* Level required: " + g.keys_level[0][0] + "\n"
        else:
            return None
        if source == "new":
            if len(g.country_names_with_keys) != 0 and len(g.country_names_with_keys) <= 10:
                commenttext += "* Available for: " + ', '.join(g.country_names_with_keys) + "\n"
            elif len(g.country_names_without_keys) != 0 and len(g.country_names_without_keys) <= 10:
                commenttext += "* Unavailable for: " + ', '.join(g.country_names_without_keys) + "\n"
            elif len(g.country_names_without_keys) != 0 and len(g.country_names_without_keys) > 10:
                commenttext += "* Unavailable for: " + ', '.join(g.continents_without_keys) + "\n"
            elif len(g.country_names_with_keys) > 10 and len(g.country_names_without_keys) > 10:
                commenttext += "* Available for: " + ', '.join(g.continents_with_keys) + "\n"
            elif len(g.country_names_with_keys) > 10 and len(g.country_names_without_keys) == 0:
                commenttext += "* No restricted countries\n"
            commenttext += "* Initial keys (at post time): " + g.keys_total + "\n"
    elif isinstance(g.keys_level, list) and source == "update" and len(g.keys_level) > 0 and g.keys_level[0][1] == '0':
        commenttext += "* Available keys: " + g.keys_total + "\n"
        commenttext += "* Level required: " + g.keys_level[0][0] + "\n"
    else:
        return None
    if source == "new":
        commenttext += '\n*Available keys are automatically updated every minute*\n'
        commenttext += '\n***\n'
    return commenttext


def buildcommenttext_igames(g, source):
    commenttext = ''
    if source == "new":
        commenttext += "**Giveaway details**\n\n"
    if isinstance(g.key_amount, str) and ((g.key_total != "0" and source == "update") or source == "new"):
        commenttext += "* Available keys: " + g.key_amount
        if g.key_claimed != "0":
            commenttext += " (" + g.key_claimed + " already claimed)"
        if source != "update":
            commenttext += "\n"
            if g.key_claimed != "0" and g.key_total != "0":
                commenttext += "* Total keys: " + g.key_total + "\n"
    else:
        return None
    if source == "new":
        commenttext += '\n*Available keys are automatically updated every minute*\n'
        commenttext += '\n***\n'
    return commenttext


def buildcommenttext(g, removed, source):
    commenttext = ''
    javascripttext = ''
    if isinstance(g.title, str):
        if source == "Indiegala" or source == "Epic":
            commenttext += '*Game with the same name on Steam:* '
        if removed:
            commenttext += '*Removed from Steam - this is information from ' + g.date + ':*\n\n'
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
        if (g.gettype == "dlc" or g.gettype == "mod") and g.basegame is not None:
            commenttext += '* Game links (**' + g.basegame[1] + '**): '
            if removed:
                commenttext += '[Store Page (archived)](' + g.basegame[6]
            else:
                commenttext += '[Store Page](https://store.steampowered.com/app/' + g.basegame[0]
            commenttext += ') | [Community Hub](https://steamcommunity.com/app/' + g.basegame[0] + ') | [SteamDB](https://steamdb.info/app/' + g.basegame[0] + ')\n\n'
        elif g.gettype == "music" and g.basegame is not None:
            if removed:
                commenttext += '* Base game ([' + g.basegame[1] + '](' + g.basegame[6] + ')) not required\n\n'
            else:
                commenttext += '* Base game ([' + g.basegame[1] + '](https://store.steampowered.com/app/' + g.basegame[0] + ')) not required\n\n'
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
            if g.price[0] == "Free" and g.price[1] == "" and g.basegame is not None and g.basegame[2] == "Free" and g.basegame[3] == "" and g.gettype == "dlc":
                commenttext += 'Game and '
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
            if g.price[0] != "No price found" and g.price[1] != "" and g.discountamount:
                commenttext += ' (' + g.discountamount + ')'
            commenttext += '\n'
            if (g.gettype == "dlc" or g.gettype == "mod") and g.basegame is not None and len(g.basegame) > 2 and (g.price[0] != "Free" or g.price[1] != "" or g.basegame[3] != "" or g.basegame[2] != "Free"):
                commenttext += ' * Game Price: '
                if g.basegame[3] != "":
                    commenttext += '~~' + g.basegame[3] + '~~ '
                commenttext += g.basegame[2]
                if not g.basegame[4] and g.basegame[2] != ("Free" and "No price found"):
                    commenttext += ' USD'
                if g.basegame[2] != "No price found" and g.basegame[3] != "" and g.basegame[5]:
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
                if int(g.achievements) == 1:
                    commenttext += ' * Has ' + str(g.achievements) + ' achievement\n'
                if int(g.achievements) > 1:
                    commenttext += ' * Has ' + str(g.achievements) + ' achievements\n'
                if len(g.cards) == 4 and g.cards[0] != 0:
                    if int(g.achievements) == 0:
                        commenttext += ' * Has no achievements\n'
                    commenttext += ' * Has ' + str(g.cards[0]) + ' trading cards'
                    if g.cards[1] != 0:
                        commenttext += ' (drops ' + str(g.cards[1]) + ')'
                    if not g.cards[3]:
                        commenttext += ' [non-marketable]'
                    if g.cards[3]:
                        commenttext += ' [^(view on Steam Market)](' + g.cards[2] + ')'
                    commenttext += '\n'
                if g.cards[0] == 0:
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
        if (g.isfree() or g.price[0] == "Free") and not g.unreleased and (source == "Steam" or g.gettype != "dlc" or (g.gettype == "dlc" and (g.isfree() or g.price[0] == "Free") and g.basegame is not None and len(g.basegame) > 2 and g.basegame[4])):
            commenttext += ' * Can be added to ASF clients with `!addlicense asf '
            if g.gettype == "dlc" and g.basegame is not None and len(g.basegame) > 2 and g.basegame[4]:
                commenttext += "a/" + g.basegame[0] + ","
            commenttext += g.asf[0] + '`\n'
            if g.asf[1] == "sub":
                javascripttext = f'javascript:AddFreeLicense({g.asf[0].strip("s/")})'
                commenttext += f' * Can be added in browsers/mobile with `{javascripttext}`\n'
        commenttext += '\n***\n'
    return commenttext, javascripttext


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
                            commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding game ' + appid)
                                    botcomment = submission.reply(commenttext)
                                    if javascripttext is not None and javascripttext != "":
                                        botcomment.reply(javascripttext)
                    elif re.search(STEAM_TITLE_REGEX, submission.title, re.IGNORECASE):
                        title_split = re.split(STEAM_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission) and game_name != "":
                            game = SteamSearchGame(game_name, False)
                            appid = game.appid
                            source_platform = "Steam"
                            if appid != 0:
                                commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                if commenttext is not None and commenttext != "":
                                    commenttext_awa = ""
                                    if re.search(ALIENWARE_URL_REGEX, submission.url):
                                        commenttext_awa = buildcommenttext_awa(AlienwareArena(submission.url, "new"), "new")
                                    if commenttext_awa is not None and commenttext_awa != "":
                                        commenttext = commenttext_awa + commenttext
                                    commenttext_igames = ""
                                    g_website = "steelseries"
                                    if re.search(CRUCIAL_URL_REGEX, submission.url):
                                        g_website = "crucial"
                                    elif re.search(IGAMES_URL_REGEX, submission.url):
                                        g_website = "igames"
                                    if (
                                        re.search(STEELSERIES_URL_REGEX, submission.url)
                                        or re.search(CRUCIAL_URL_REGEX, submission.url)
                                        or re.search(IGAMES_URL_REGEX, submission.url)
                                    ):
                                        g_id = re.search('\d+', submission.url).group(0)
                                        commenttext_igames = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                    if commenttext_igames is not None and commenttext_igames != "":
                                        commenttext = commenttext_igames + commenttext
                                    commenttext += buildfootertext()
                                    if len(commenttext) < 10000:
                                        print('Commenting on post ' + str(submission) + ' after finding game ' + game_name)
                                        botcomment = submission.reply(commenttext)
                                        if javascripttext is not None and javascripttext != "":
                                            botcomment.reply(javascripttext)
                            else:
                                game = SteamSearchGame(game_name, True)
                                appid = game.appid
                                if appid != 0:
                                    # try for only removed store page
                                    commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                    if commenttext is None or commenttext == "":
                                        # not available on Steam
                                        commenttext, javascripttext = buildcommenttext(SteamRemovedGame(appid), True, source_platform)
                                    if commenttext is not None and commenttext != "":
                                        commenttext_awa = ""
                                        if re.search(ALIENWARE_URL_REGEX, submission.url):
                                            commenttext_awa = buildcommenttext_awa(AlienwareArena(submission.url, "new"), "new")
                                        if commenttext_awa is not None and commenttext_awa != "":
                                            commenttext = commenttext_awa + commenttext
                                        commenttext_igames = ""
                                        g_website = "steelseries"
                                        if re.search(CRUCIAL_URL_REGEX, submission.url):
                                            g_website = "crucial"
                                        elif re.search(IGAMES_URL_REGEX, submission.url):
                                            g_website = "igames"
                                        if (
                                            re.search(STEELSERIES_URL_REGEX, submission.url)
                                            or re.search(CRUCIAL_URL_REGEX, submission.url)
                                            or re.search(IGAMES_URL_REGEX, submission.url)
                                        ):
                                            g_id = re.search('\d+', submission.url).group(0)
                                            commenttext_igames = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                        if commenttext_igames is not None and commenttext_igames != "":
                                            commenttext = commenttext_igames + commenttext
                                        commenttext += buildfootertext()
                                        if len(commenttext) < 10000:
                                            print('Commenting on post ' + str(submission) + ' after finding removed game ' + game_name)
                                            botcomment = submission.reply(commenttext)
                                            if javascripttext is not None and javascripttext != "":
                                                botcomment.reply(javascripttext)
                                elif (
                                    re.search(STEELSERIES_URL_REGEX, submission.url)
                                    or re.search(CRUCIAL_URL_REGEX, submission.url)
                                    or re.search(IGAMES_URL_REGEX, submission.url)
                                ):
                                    # Not found on Steam, still post key availability part
                                    g_website = "steelseries"
                                    if re.search(CRUCIAL_URL_REGEX, submission.url):
                                        g_website = "crucial"
                                    elif re.search(IGAMES_URL_REGEX, submission.url):
                                        g_website = "igames"
                                    g_id = re.search('\d+', submission.url).group(0)
                                    commenttext = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                    if commenttext is not None and commenttext != "":
                                        commenttext += buildfootertext()
                                        if len(commenttext) < 10000:
                                            print('Commenting on post ' + str(submission) + ' after finding ' + g_website + ' domain')
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
                        if fitscriteria(submission) and game_name != "":
                            game = SteamSearchGame(game_name, False)
                            appid = game.appid
                            if appid != 0:
                                commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                if commenttext is not None and commenttext != "":
                                    commenttext += buildfootertext()
                                    if len(commenttext) < 10000:
                                        print('Commenting on post ' + str(submission) + ' after finding game ' + game_name)
                                        submission.reply(commenttext)
                    elif re.search(ALIENWARE_URL_REGEX, submission.url):
                        if fitscriteria(submission):
                            commenttext = buildcommenttext_awa(AlienwareArena(submission.url, "new"), "new")
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding Alienware Arena domain')
                                    submission.reply(commenttext)
                    elif (
                        re.search(STEELSERIES_URL_REGEX, submission.url)
                        or re.search(CRUCIAL_URL_REGEX, submission.url)
                        or re.search(IGAMES_URL_REGEX, submission.url)
                    ):
                        if fitscriteria(submission):
                            g_website = "steelseries"
                            if re.search(CRUCIAL_URL_REGEX, submission.url):
                                g_website = "crucial"
                            elif re.search(IGAMES_URL_REGEX, submission.url):
                                g_website = "igames"
                            g_id = re.search('\d+', submission.url).group(0)
                            commenttext = buildcommenttext_igames(iGames(g_id, g_website), "new")
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding ' + g_website + ' domain')
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
                        javascripts = []
                        source_platform = "Steam"
                        if (
                            (indiegala := re.search(INDIEGALA_TITLE_REGEX, comment.submission.title, re.IGNORECASE)
                                and re.search(INDIEGALA_URL_REGEX, comment.submission.url))
                            or (epic := re.search(EPIC_TITLE_REGEX, comment.submission.title, re.IGNORECASE)
                                and re.search(EPIC_URL_REGEX, comment.submission.url))
                            or (itch := re.search(ITCH_URL_REGEX, comment.submission.url))
                        ):
                            if indiegala is not None:
                                source_platform = "Indiegala_comment"
                            elif epic is not None:
                                source_platform = "Epic_comment"
                            elif itch is not None:
                                source_platform = "Itch_comment"
                        for i in range(len(games)):
                            appid = re.search('\d+', games[i]).group(0)
                            make_comment, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                            if make_comment is not None and make_comment != "":
                                commenttext += make_comment
                                appids.append(appid)
                            if javascripttext is not None and javascripttext != "":
                                javascripts.append(javascripttext)
                        if commenttext != "":
                            commenttext += buildfootertext()
                            if len(commenttext) < 10000:
                                print('Replying to comment ' + str(comment) + ' after finding game ' + ', '.join(appids))
                                botcomment = comment.reply(commenttext)
                                if len(javascripts) > 0:
                                    for text in javascripts:
                                        botcomment.reply(text)
            except PrawcoreException:
                print('Trying to reach Reddit')
                time.sleep(30)


class EditCommentWatch(threading.Thread):
    def run(self):
        print('Watching bot comments')
        while True:
            try:
                count = 0
                for comment in reddit.redditor(BOT_USERNAME).comments.new(limit=20):
                    now = time.time()
                    age = now - comment.created_utc  # in seconds
                    if age <= 14400 and comment.body.startswith('**Giveaway details**'):
                        count += 1
                if count > 0:
                    seconds = 60
                    if count > 11:
                        seconds = 120
                    for comment in reddit.redditor(BOT_USERNAME).comments.new(limit=20):
                        now = time.time()
                        age = now - comment.created_utc  # in seconds
                        if age <= 14400 and comment.body.startswith('**Giveaway details**'):
                            sleep_time = seconds / count
                            time.sleep(sleep_time)  # try edit(s) every minute
                            if re.search(ALIENWARE_URL_REGEX, comment.submission.url):
                                g_website = "alienware"
                                split_part = "* Unavailable for:"
                            elif re.search(STEELSERIES_URL_REGEX, comment.submission.url):
                                g_website = "steelseries"
                                split_part = "\n* Total keys:"
                            elif re.search(CRUCIAL_URL_REGEX, comment.submission.url):
                                g_website = "crucial"
                                split_part = "\n* Total keys:"
                            elif re.search(IGAMES_URL_REGEX, comment.submission.url):
                                g_website = "igames"
                                split_part = "\n* Total keys:"
                            if g_website == "alienware":
                                edited_part = buildcommenttext_awa(AlienwareArena(comment.submission.url, "update"), "update")
                            else:
                                g_id = re.search('\d+', comment.submission.url).group(0)
                                edited_part = buildcommenttext_igames(iGames(g_id, g_website), "update")
                            original_body = comment.body
                            original_body_split = original_body.split("**Giveaway details**\n\n")
                            if g_website == "alienware":
                                split_test = original_body_split[1].split(split_part, 1)
                                if len(split_test) == 1:
                                    split_part = "* Available for:"
                                    split_test = original_body_split[1].split(split_part, 1)
                                    if len(split_test) == 1:
                                        split_part = "* No restricted countries"
                            part_to_edit = original_body_split[1].split(split_part, 1)[0]
                            if g_website == "steelseries" or g_website == "crucial" or g_website == "igames":
                                test_out_of_keys = re.sub("[^0-9]", "", part_to_edit)
                                if test_out_of_keys.startswith('0'):
                                    # prevents edits on a restock, leads to incorrect keys
                                    edited_part = part_to_edit
                            original_body_part = original_body_split[1].split(split_part, 1)[1]
                            edited_comment = ""
                            if edited_part != part_to_edit:
                                try:
                                    edited_comment = "**Giveaway details**\n\n" + edited_part + split_part + original_body_part
                                except TypeError:
                                    continue
                                if len(edited_comment) < 10000:
                                    comment.edit(edited_comment)
            except PrawcoreException:
                print('Trying to reach Reddit')
                time.sleep(30)


class EditCommentWatchLong(threading.Thread):
    def run(self):
        print('Watching longlasting bot comments')
        while True:
            try:
                count = 0
                for comment in reddit.redditor(BOT_USERNAME).comments.new(limit=20):
                    now = time.time()
                    age = now - comment.created_utc  # in seconds
                    if age > 14400 and comment.body.startswith('**Giveaway details**'):
                        count += 1
                if count > 0:
                    seconds = 600
                    if count > 11:
                        seconds = 1200
                    for comment in reddit.redditor(BOT_USERNAME).comments.new(limit=20):
                        now = time.time()
                        age = now - comment.created_utc  # in seconds
                        if age > 14400 and comment.body.startswith('**Giveaway details**'):
                            sleep_time = seconds / count
                            time.sleep(sleep_time)  # try edit(s) every 10 minutes
                            if re.search(ALIENWARE_URL_REGEX, comment.submission.url):
                                g_website = "alienware"
                                split_part = "* Unavailable for:"
                            elif re.search(STEELSERIES_URL_REGEX, comment.submission.url):
                                g_website = "steelseries"
                                split_part = "\n* Total keys:"
                            elif re.search(CRUCIAL_URL_REGEX, comment.submission.url):
                                g_website = "crucial"
                                split_part = "\n* Total keys:"
                            elif re.search(IGAMES_URL_REGEX, comment.submission.url):
                                g_website = "igames"
                                split_part = "\n* Total keys:"
                            if g_website == "alienware":
                                edited_part = buildcommenttext_awa(AlienwareArena(comment.submission.url, "update"), "update")
                            else:
                                g_id = re.search('\d+', comment.submission.url).group(0)
                                edited_part = buildcommenttext_igames(iGames(g_id, g_website), "update")
                            original_body = comment.body
                            original_body_split = original_body.split("**Giveaway details**\n\n")
                            if g_website == "alienware":
                                split_test = original_body_split[1].split(split_part, 1)
                                if len(split_test) == 1:
                                    split_part = "* Available for:"
                                    split_test = original_body_split[1].split(split_part, 1)
                                    if len(split_test) == 1:
                                        split_part = "* No restricted countries"
                            part_to_edit = original_body_split[1].split(split_part, 1)[0]
                            if g_website == "steelseries" or g_website == "crucial" or g_website == "igames":
                                test_out_of_keys = re.sub("[^0-9]", "", part_to_edit)
                                if test_out_of_keys.startswith('0'):
                                    # prevents edits on a restock, leads to incorrect keys
                                    edited_part = part_to_edit
                            original_body_part = original_body_split[1].split(split_part, 1)[1]
                            edited_comment = ""
                            if edited_part != part_to_edit:
                                try:
                                    edited_comment = "**Giveaway details**\n\n" + edited_part + split_part + original_body_part.replace("are automatically updated every minute", "are automatically updated every 10 minutes")
                                except TypeError:
                                    continue
                                if len(edited_comment) < 10000:
                                    comment.edit(edited_comment)
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
    reddit.validate_on_submit = True

    subwatch = SubWatch()
    commentwatch = CommentWatch()
    editcommentwatch = EditCommentWatch()
    editcommentwatchlong = EditCommentWatchLong()

    subwatch.start()
    commentwatch.start()
    editcommentwatch.start()
    editcommentwatchlong.start()
