# Reddit FreeGameFindings Bot
# Resolves Steam URLs from submissions, and comments information about them

import os
import re
import threading
import time
from humanfriendly import format_timespan

import praw
from prawcore.exceptions import PrawcoreException

from SteamGame import SteamGame
from SteamRemovedGame import SteamRemovedGame
from SteamSearchGame import SteamSearchGame
from GOGGame import GOGGame
from AlienwareArena import AlienwareArena
from iGames import iGames
from Keyhub import Keyhub
from EpicGame import EpicGame
from Giveeclub import GiveeClub
from Gleam import Gleam

BLOCKED_USER_FILE = 'blockedusers.txt'  # Will not reply to these people
SUBLIST = "FreeGameFindings"

BOT_USERNAME = os.getenv("RSGIB_USERNAME")

STEAM_APPURL_REGEX = r"((https?:\/\/)?)(store.steampowered.com(\/agecheck)?\/app\/\d+)"
STEAMDB_APPURL_REGEX = r"((https?:\/\/)?)(steamdb.info\/app\/\d+)"
STEAM_TITLE_REGEX = r"\[.*(Steam).*\]\s*\((Game|DLC|Beta|Alpha)\)"
STEAM_PLATFORM_REGEX = r"\[.*(Steam).*\]"
INDIEGALA_URL_REGEX = r"((https?:\/\/)?)(freebies.indiegala.com\/)"
INDIEGALA_TITLE_REGEX = r"\[.*(Indiegala).*\]\s*\((Game)\)"
EPIC_TITLE_REGEX = r"\[.*(Epic).*\]\s*\((Game)\)"
GOG_URL_REGEX = r"((https?:\/\/)?)(gog.com\/\w*\/*game)"
GOG_TITLE_REGEX = r"\[.*(GOG).*\]\s*\((Game|DLC|Beta|Alpha|Other)\)"
ALIENWARE_URL_REGEX = r"(https?:\/\/)?(\b)?\.?(alienwarearena.com\/\w+)"
STEELSERIES_URL_REGEX = r"((https?:\/\/)?)(games.steelseries.com\/giveaway\/\d+)"
CRUCIAL_URL_REGEX = r"((https?:\/\/)?)(games.crucial.com\/promotions\/\d+)"
IGAMES_URL_REGEX = r"((https?:\/\/)?)(igames.gg\/promotions\/\d+)"
KEYHUB_URL_REGEX = r"((https?:\/\/)?)(key-hub.eu\/giveaway\/\d+)"
GLEAMIO_URL_REGEX = r"((https?:\/\/)?)(gleam.io)"
RANDOM_TITLE_REGEX = r"(Random).*(Game)"
GIVEECLUB_URL_REGEX = r"((https?:\/\/)?)givee\.club(?:/[^/]+)?/event/(\d+)"


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
    if isinstance(g.keys_tier, list) and len(g.keys_tier) > 0 and (g.keys_tier[0][1] != '0' or (len(g.keys_tier) > 1 and g.keys_tier[1][1] != '0')):
        if source == "update" or len(g.keys_tier) != 0:
            commenttext += "* Available keys: " + g.keys_tier[0][1] + "\n"
            commenttext += "* Tier required: " + g.keys_tier[0][0] + "\n"
        else:
            return None
        if source == "new":
            if len(g.country_names_with_keys) != 0 and len(g.country_names_with_keys) <= 10:
                commenttext += "* Keys available for: " + ', '.join(g.country_names_with_keys) + "\n"
            elif len(g.country_names_without_keys) != 0:
                commenttext += "* No keys for: " + ', '.join(g.country_names_without_keys) + "\n"
            elif len(g.country_names_with_keys) > 10 and len(g.country_names_without_keys) == 0:
                commenttext += "* Keys available for all countries\n"
            commenttext += "* Total keys: " + g.keys_tier[0][1] + "\n"
    elif isinstance(g.keys_tier, list) and source == "update" and len(g.keys_tier) > 0 and g.keys_tier[0][1] == '0':
        commenttext += "* Available keys: " + g.keys_tier[0][1] + "\n"
        commenttext += "* Tier required: " + g.keys_tier[0][0] + "\n"
    else:
        return None
    if source == "new":
        commenttext += '\n*Updating available keys every minute*\n'
        commenttext += '\n***\n'
    return commenttext


def buildcommenttext_igames(g, source):
    commenttext = ''
    if source == "new":
        commenttext += "**Giveaway details**\n\n"
    if isinstance(g.key_amount, str) and ((g.key_total != "0" and source == "update") or source == "new") and not g.gg_app:
        commenttext += "* Available keys: " + g.key_amount
        if g.key_claimed != "0":
            commenttext += "\n"
            commenttext += "* Keys already claimed: " + g.key_claimed
        if source != "update":
            commenttext += "\n"
            if g.key_claimed != "0" and g.key_total != "0":
                commenttext += "* Total keys: " + g.key_total + "\n"
    else:
        return None
    if source == "new":
        commenttext += '\n*Updating available keys every minute*\n'
        commenttext += '\n***\n'
    return commenttext


def buildcommenttext_keyhub(g, source):
    commenttext = ''
    if source == "new":
        commenttext += "**Giveaway details**\n\n"
    if isinstance(g.key_amount, str) and ((g.key_amount != "0" and source == "new") or source == "update"):
        commenttext += "* Available keys: " + g.key_amount + "\n"
        if source == "new":
            commenttext += "* Steam level required: " + g.level + "\n"
            commenttext += "* Total keys: " + g.key_amount + "\n"
    else:
        return None
    if source == "new":
        commenttext += '\n*Updating available keys every minute*\n'
        commenttext += '\n***\n'
    return commenttext


def buildcommenttext_gog(g):
    commenttext = ''
    if isinstance(g.title, str):
        commenttext += '**' + g.title + '**'
        commenttext += '\n\n'
        commenttext += '[GOG Store Page](' + "https://www.gog.com/game/" + g.gog_link + ")"
        if g.steamgame.appid != 0:
            commenttext += " | [Steam Store Page](" + "https://store.steampowered.com/app/" + g.steamgame.appid + ")"
        if g.gettype == "game" and g.pcgamingwiki:
            commenttext += " | [PCGamingWiki](https://www.pcgamingwiki.com/api/appid.php?appid=" + g.steamgame.appid + ')'
        commenttext += '\n\n'
        if g.steamreviews:
            commenttext += ' * '
        commenttext += 'GOG Reviews: '
        commenttext += g.reviewsummary
        if g.reviewdetails:
            commenttext += g.reviewdetails
        if g.steamreviews:
            commenttext += '\n'
            commenttext += ' * Steam Reviews: '
            commenttext += g.steamreviews
        commenttext += '\n\n'
        if g.blurb:
            commenttext += '*' + g.blurb + '*\n\n'
        if g.releasedate:
            commenttext += ' * '
            if g.gettype == "dlc":
                commenttext += 'DLC '
            commenttext += 'Release Date: ' + g.releasedate
            commenttext += '\n'
        if g.developers:
            commenttext += ' * Developer'
            if len(g.developers) > 1:
                commenttext += 's'
            commenttext += ': ' + ", ".join(g.developers) + '\n'
        if g.features:
            commenttext += ' * GOG Features: ' + ", ".join(g.features) + '\n'
        if g.os:
            commenttext += ' * Operating System'
            if len(g.os) > 1:
                commenttext += 's'
            commenttext += ': ' + ", ".join(g.os) + '\n'
        if g.genres_tags and len(g.genres_tags) != 0:
            commenttext += ' * Genre/Tags: ' + ", ".join(g.genres_tags) + '\n'
        commenttext += '\n***\n'
    return commenttext


def buildcommenttext_epic(g):
    commenttext = ''
    if g.checkout_link != "" or g.android_checkout != "" or g.ios_checkout != "":
        commenttext += "**Giveaway details**\n\n"
        commenttext += "Instant checkout: "
        if g.android_checkout != "" or g.ios_checkout != "":
            commenttext += "\n"
            if g.checkout_link and g.checkout_link != "":
                commenttext += "\n * [PC](https://store.epicgames.com/purchase?"
                commenttext += g.checkout_link
                commenttext += ")"
            if g.android_checkout != "":
                commenttext += "\n * [Android](https://store.epicgames.com/purchase?"
                commenttext += g.android_checkout
                commenttext += ")"
            if g.ios_checkout != "":
                commenttext += "\n * [iOS](https://store.epicgames.com/purchase?"
                commenttext += g.ios_checkout
                commenttext += ")"
            if (
                    (g.checkout_link and g.android_checkout) or
                    (g.checkout_link and g.ios_checkout) or
                    (g.android_checkout and g.ios_checkout)
            ):
                if g.checkout_link and g.android_checkout and g.ios_checkout:
                    commenttext += "\n * [PC + Android + iOS](https://store.epicgames.com/purchase?"
                elif g.checkout_link and g.android_checkout and not g.ios_checkout:
                    commenttext += "\n * [PC + Android](https://store.epicgames.com/purchase?"
                elif g.checkout_link and g.ios_checkout and not g.android_checkout:
                    commenttext += "\n * [PC + iOS](https://store.epicgames.com/purchase?"
                elif g.android_checkout and g.ios_checkout and not g.checkout_link:
                    commenttext += "\n * [Android + iOS](https://store.epicgames.com/purchase?"
                if g.checkout_link and g.checkout_link != "":
                    commenttext += g.checkout_link + "&"
                if g.android_checkout != "":
                    commenttext += g.android_checkout + "&"
                if g.ios_checkout != "":
                    commenttext += g.ios_checkout
                commenttext += ")"
        elif g.checkout_link and g.checkout_link != "":
            commenttext += "https://store.epicgames.com/purchase?"
            commenttext += g.checkout_link
        commenttext += "\n"
        if isinstance(g.blacklisted_countries, str) and g.blacklisted_countries != "":
            commenttext += "* Blacklisted countries: " + ', '.join(g.blacklisted_countries)
            commenttext += "\n"
        commenttext += '\n***\n'
    else:
        return None
    return commenttext


def buildcommenttext_giveeclub(g):
    commenttext = ''
    if not g.tasks:
        return None
    commenttext += "**Giveaway details**\n\n"
    commenttext += "Tasks:\n\n"
    for i, task in enumerate(g.tasks, 1):
        commenttext += f"{i}. {task['description']}\n"
    commenttext += '\n***\n'
    return commenttext


def buildcommenttext_gleam(g):
    commenttext = ''
    if not g.tasks:
        return None
    commenttext += "**Giveaway details**\n\n"
    commenttext += "\n".join(g.commenttext)
    commenttext += '\n'
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
        commenttext += '[SteamDB](https://steamdb.info/app/' + g.appID + ')'
        if g.gettype == "game" and g.pcgamingwiki:
            commenttext += ' | [PCGamingWiki](https://www.pcgamingwiki.com/api/appid.php?appid=' + g.appID + ')'
        commenttext += '\n'
        if (g.gettype == "dlc" or g.gettype == "mod") and g.basegame is not None:
            commenttext += '* '
            if g.basegame[2] == "Free":
                commenttext += 'Free'
            else:
                commenttext += 'Paid'
            commenttext += ' Base Game: **' + g.basegame[1] + '** - '
            if removed:
                commenttext += '[Store Page (archived)](' + g.basegame[6]
            else:
                commenttext += '[Store Page](https://store.steampowered.com/app/' + g.basegame[0]
            commenttext += ') | [Community Hub](https://steamcommunity.com/app/' + g.basegame[0] + ') | [SteamDB](https://steamdb.info/app/' + g.basegame[0] + ')'
            if g.basegame[6]:
                commenttext += ' | [PCGamingWiki](https://www.pcgamingwiki.com/api/appid.php?appid=' + g.basegame[0] + ')'
            commenttext += '\n\n'
        elif g.gettype == "music" and g.basegame is not None:
            if removed:
                commenttext += '* Base game ([' + g.basegame[1] + '](' + g.basegame[6] + ')) not required\n\n'
            else:
                commenttext += '* Base game ([' + g.basegame[1] + '](https://store.steampowered.com/app/' + g.basegame[0] + ')) not required\n\n'
        else:
            commenttext += '\n'
        if not g.unreleased and (g.reviewsummary != "" or g.reviewdetails != ""):
            if g.gettype == "dlc":
                commenttext += 'DLC '
            commenttext += 'Reviews: '
            if g.reviewdetails != "" and g.lowreviews:
                commenttext += g.reviewdetails
                if not removed:
                    commenttext += " ^(includes key reviews)"
            elif g.reviewdetails != "" and g.reviewdetails is not None:
                if "user reviews" in g.reviewsummary:
                    commenttext += g.reviewdetails
                else:
                    commenttext += g.reviewsummary + g.reviewdetails
            else:
                commenttext += g.reviewsummary
            if g.steamdbrating:
                commenttext += ' | SteamDB Rating: ' + g.steamdbrating + '%'
            commenttext += '\n\n'
        if g.blurb != "":
            commenttext += '*' + g.blurb + '*\n\n'
        if g.unreleased:
            if g.unreleasedtext is None:
                commenttext += " * Isn't released yet\n"
            else:
                commenttext += ' * ' + g.unreleasedtext
                if g.isearlyaccess:
                    commenttext += ' (Early Access)'
                commenttext += '\n'
        if not removed and not (g.unreleased and g.price[0] == "No price found"):
            commenttext += ' * '
            if g.gettype == "dlc" and g.price[0] == "Free" and g.price[1] == "" and g.basegame is not None and g.basegame[2] == "Free" and g.basegame[3] == "":
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
            commenttext += ' * '
            if g.gettype == "dlc":
                commenttext += 'DLC '
            commenttext += 'Release Date: ' + g.releasedate
            if g.isearlyaccess:
                commenttext += ' (Early Access)'
            commenttext += '\n'
        if g.developers:
            commenttext += ' * Developer'
            if g.developers_num > 1:
                commenttext += 's'
            commenttext += ': ' + g.developers + '\n'
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
                    if g.cards[1] != 0 and not g.isfree():
                        commenttext += ' (drops ' + str(g.cards[1]) + ')'
                    elif g.cards[1] != 0 and g.isfree():
                        commenttext += ' (no drops)'
                    if not g.cards[3]:
                        commenttext += ' [non-marketable]'
                    if g.cards[3]:
                        commenttext += ' [^(view on Steam Market)](' + g.cards[2] + ')'
                    commenttext += '\n'
                if len(g.cards) == 3 and g.cards[0] != 0:
                    if int(g.achievements) == 0:
                        commenttext += ' * Has no achievements\n'
                    commenttext += ' * Has trading cards'
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
            commenttext += ' +1 game count [^(what is +1?)](https://www.reddit.com/r/FreeGameFindings/wiki/faq/#wiki_what_is_.2B1.3F)\n'
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


def repostwatch_title(title):
    repost_title_regex = r"[.;?!]$"
    if re.search(repost_title_regex, title):
        return True
    else:
        return False


def repostwatch_duplicate(submission):
    for duplicate in submission.duplicates():
        if duplicate.subreddit == SUBLIST:
            created_time = duplicate.created_utc
            now = time.time()
            age = now - created_time
            days_364 = 31449600
            days_366 = 31622400
            if days_364 <= age <= days_366:
                return True
            else:
                return False


def buildcommenttext_repost(submission):
    commenttext = 'I have detected that this may be a false submission from a repost bot, and have therefore removed this submission as a precaution.\n\nIf this is a mistake, please send a message to us with [this link]'
    commenttext += '(https://www.reddit.com/message/compose?to=%2Fr%2Ffreegamefindings&subject=FGF%20bot%20removed%20my%20post%2C%20please%20approve%20it%20if%20it%20conforms%20to%20the%20subreddit%20rules.&message=FGF%20bot%20removed%20my%20post%2C%20please%20approve%20it%20if%20it%20conforms%20to%20the%20subreddit%20rules.%20https://www.reddit.com' + submission.permalink + ')'
    commenttext += ' and we will approve it as soon as possible.'
    return commenttext


class SubWatch(threading.Thread):
    def run(self):
        print('Started watching subs: ' + SUBLIST)
        subreddit = reddit.subreddit(SUBLIST)
        while True:
            try:
                for submission in subreddit.stream.submissions():
                    if submission.banned_by is not None:
                        continue
                    if (
                        re.search(STEAM_APPURL_REGEX, submission.url)
                        or re.search(STEAMDB_APPURL_REGEX, submission.url)
                    ):
                        appid = re.search(r'\d+', submission.url).group(0)
                        source_platform = "Steam"
                        if fitscriteria(submission):
                            commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding game ' + appid, flush=True)
                                    botcomment = submission.reply(commenttext)
                                    if javascripttext is not None and javascripttext != "":
                                        botcomment.reply(javascripttext)
                                    if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                        # Set post as NSFW
                                        submission.mod.nsfw()
                                    if "* Paid Base Game:" in commenttext:
                                        # Check for paid base game DLC
                                        flair_text = submission.link_flair_text
                                        if flair_text is None:
                                            # if no flair exists
                                            new_text = "Paid Base Game"
                                            submission.mod.flair(text=new_text, css_class="BasePaid", flair_template_id="129ebd48-becd-11ed-9399-b250c43c4702")
                                        elif "paid base game" not in flair_text.lower():
                                            # if not yet in flair
                                            flair_id = submission.link_flair_template_id
                                            new_text = flair_text + " | Paid Base Game"
                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
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
                                        g_id = re.search(r'\d+', submission.url).group(0)
                                        commenttext_igames = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                    if commenttext_igames is not None and commenttext_igames != "":
                                        commenttext = commenttext_igames + commenttext
                                    commenttext_keyhub = ""
                                    if re.search(KEYHUB_URL_REGEX, submission.url):
                                        commenttext_keyhub = buildcommenttext_keyhub(Keyhub(submission.url, "new"), "new")
                                    if commenttext_keyhub is not None and commenttext_keyhub != "":
                                        commenttext = commenttext_keyhub + commenttext
                                    commenttext_giveeclub = ""
                                    if re.search(GIVEECLUB_URL_REGEX, submission.url):
                                        commenttext_giveeclub = buildcommenttext_giveeclub(GiveeClub(submission.url))
                                    if commenttext_giveeclub is not None and commenttext_giveeclub != "":
                                        commenttext = commenttext_giveeclub + commenttext
                                    commenttext_gleam = ""
                                    if re.search(GLEAMIO_URL_REGEX, submission.url):
                                        commenttext_gleam = buildcommenttext_gleam(Gleam(submission.url))
                                    if commenttext_gleam is not None and commenttext_gleam != "":
                                        commenttext = commenttext_gleam + commenttext
                                    commenttext += buildfootertext()
                                    if len(commenttext) < 10000:
                                        print('Commenting on post ' + str(submission) + ' after finding game ' + game_name, flush=True)
                                        botcomment = submission.reply(commenttext)
                                        if javascripttext is not None and javascripttext != "":
                                            botcomment.reply(javascripttext)
                                        if commenttext_awa is not None and commenttext_awa != "":
                                            flair_text = submission.link_flair_text
                                            tier_number = commenttext_awa.split("Tier required: ")[1].split()[0]
                                            if "Tier required: 1" not in commenttext_awa and "* Keys available for all countries\n" not in commenttext_awa:
                                                # flair post with prior work required, regional issues and add tier
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues"
                                                    submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                elif "prior work" not in flair_text.lower() and "regional" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                elif "regional" not in flair_text.lower():
                                                    # if regional not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Tier " + tier_number + "+ | Regional Issues | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if "Tier required: 1" not in commenttext_awa and "* Keys available for all countries\n" in commenttext_awa:
                                                # flair post with prior work required and add tier
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Tier " + tier_number + "+ | Prior Work Required"
                                                    submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                elif "prior work" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Tier " + tier_number + "+ | Prior Work Required | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if "* Keys available for all countries\n" not in commenttext_awa and "Tier required: 1" in commenttext_awa:
                                                # flair post with regional issues
                                                if flair_text is None:
                                                    # if no flair exists
                                                    submission.mod.flair(text="Regional Issues", css_class="Regionlocked", flair_template_id="b3a089de-2437-11e6-8bda-0e93018c4773")
                                                elif "regional" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = flair_text + " | Regional Issues"
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                        if commenttext_keyhub is not None and commenttext_keyhub != "":
                                            flair_text = submission.link_flair_text
                                            level_number = commenttext_keyhub.split("Steam level required: ")[1].split()[0]
                                            if flair_text is None:
                                                # if no flair exists
                                                new_text = "Steam level " + level_number + "+"
                                                submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                            elif "level" not in flair_text.lower():
                                                # if not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = "Steam level " + level_number + "+ | " + flair_text
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                        if commenttext_giveeclub is not None and commenttext_giveeclub != "":
                                            flair_text = submission.link_flair_text
                                            level_number = commenttext_giveeclub.split("profile level on Steam")[0].split()[-1]
                                            if flair_text is None:
                                                # if no flair exists
                                                new_text = "Steam level " + level_number
                                                submission.mod.flair(text=new_text, css_class="ReadComments",
                                                                     flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                            elif "level" not in flair_text.lower():
                                                # if not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = "Steam level " + level_number + " | " + flair_text
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                        if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                            # Set post as NSFW
                                            submission.mod.nsfw()
                                        if "* Paid Base Game:" in commenttext:
                                            # Check for paid base game DLC
                                            flair_text = submission.link_flair_text
                                            if flair_text is None:
                                                # if no flair exists
                                                new_text = "Paid Base Game"
                                                submission.mod.flair(text=new_text, css_class="BasePaid", flair_template_id="129ebd48-becd-11ed-9399-b250c43c4702")
                                            elif "paid base game" not in flair_text.lower():
                                                # if not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = flair_text + " | Paid Base Game"
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
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
                                            g_id = re.search(r'\d+', submission.url).group(0)
                                            commenttext_igames = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                        if commenttext_igames is not None and commenttext_igames != "":
                                            commenttext = commenttext_igames + commenttext
                                        commenttext_keyhub = ""
                                        if re.search(KEYHUB_URL_REGEX, submission.url):
                                            commenttext_keyhub = buildcommenttext_keyhub(Keyhub(submission.url, "new"), "new")
                                        if commenttext_keyhub is not None and commenttext_keyhub != "":
                                            commenttext = commenttext_keyhub + commenttext
                                        commenttext_giveeclub = ""
                                        if re.search(GIVEECLUB_URL_REGEX, submission.url):
                                            commenttext_giveeclub = buildcommenttext_giveeclub(
                                                GiveeClub(submission.url))
                                        if commenttext_giveeclub is not None and commenttext_giveeclub != "":
                                            commenttext = commenttext_giveeclub + commenttext
                                        commenttext_gleam = ""
                                        if re.search(GLEAMIO_URL_REGEX, submission.url):
                                            commenttext_gleam = buildcommenttext_gleam(Gleam(submission.url))
                                        if commenttext_gleam is not None and commenttext_gleam != "":
                                            commenttext = commenttext_gleam + commenttext
                                        commenttext += buildfootertext()
                                        if len(commenttext) < 10000:
                                            print('Commenting on post ' + str(submission) + ' after finding removed game ' + game_name, flush=True)
                                            botcomment = submission.reply(commenttext)
                                            if javascripttext is not None and javascripttext != "":
                                                botcomment.reply(javascripttext)
                                            flair_text = submission.link_flair_text
                                            if commenttext.startswith("*Removed from Steam"):
                                                if flair_text is None:
                                                    # flair post with delisted if no flair exists
                                                    submission.mod.flair(text="Delisted Game", css_class="DelistedGame", flair_template_id="9a5196c4-8865-11ec-8a1f-8261ed8ecd20")
                                                elif "delisted" not in flair_text.lower():
                                                    # flair post with delisted if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = flair_text + " | Delisted Game"
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if commenttext_awa is not None and commenttext_awa != "":
                                                tier_number = commenttext_awa.split("Tier required: ")[1].split()[0]
                                                if "Tier required: 1" not in commenttext_awa and "* Keys available for all countries\n" not in commenttext_awa:
                                                    # flair post with prior work required, regional issues and add tier
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues"
                                                        submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                    elif "prior work" not in flair_text.lower() and "regional" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues" + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                    elif "regional" not in flair_text.lower():
                                                        # if regional not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Tier " + tier_number + "+ | Regional Issues | " + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if "Tier required: 1" not in commenttext_awa and "* Keys available for all countries\n" in commenttext_awa:
                                                    # flair post with prior work required and add tier
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required"
                                                        submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                    elif "prior work" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required | " + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if "* Keys available for all countries\n" not in commenttext_awa and "Tier required: 1" in commenttext_awa:
                                                    # flair post with regional issues
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        submission.mod.flair(text="Regional Issues", css_class="Regionlocked", flair_template_id="b3a089de-2437-11e6-8bda-0e93018c4773")
                                                    elif "regional" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = flair_text + " | Regional Issues"
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if commenttext_keyhub is not None and commenttext_keyhub != "":
                                                flair_text = submission.link_flair_text
                                                level_number = commenttext_keyhub.split("Steam level required: ")[1].split()[0]
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Steam level " + level_number + "+"
                                                    submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                                elif "level" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Steam level " + level_number + "+ | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if commenttext_giveeclub is not None and commenttext_giveeclub != "":
                                                flair_text = submission.link_flair_text
                                                level_number = commenttext.split("profile level on Steam")[0].split()[-1]
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Steam level " + level_number
                                                    submission.mod.flair(text=new_text, css_class="ReadComments",
                                                                         flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                                elif "level" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Steam level " + level_number + " | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                                # Set post as NSFW
                                                submission.mod.nsfw()
                                            if "* Paid Base Game:" in commenttext:
                                                # Check for paid base game DLC
                                                flair_text = submission.link_flair_text
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Paid Base Game"
                                                    submission.mod.flair(text=new_text, css_class="BasePaid", flair_template_id="129ebd48-becd-11ed-9399-b250c43c4702")
                                                elif "paid base game" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = flair_text + " | Paid Base Game"
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                    elif (
                                        re.search(STEELSERIES_URL_REGEX, submission.url)
                                        or re.search(CRUCIAL_URL_REGEX, submission.url)
                                        or re.search(IGAMES_URL_REGEX, submission.url)
                                        or re.search(ALIENWARE_URL_REGEX, submission.url)
                                        or re.search(KEYHUB_URL_REGEX, submission.url)
                                        or re.search(GIVEECLUB_URL_REGEX, submission.url)
                                        or re.search(GLEAMIO_URL_REGEX, submission.url)
                                    ):
                                        # Not found on archive.org, post steamdb and key availability part
                                        commenttext += '*Removed from Steam, no information found on archive.org*\n\n'
                                        commenttext += '**' + game_name +'**\n\n'
                                        commenttext += '[Community Hub](https://steamcommunity.com/app/' + game.appid + ') | '
                                        commenttext += '[SteamDB](https://steamdb.info/app/' + game.appid + ')\n\n***\n'
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
                                            g_id = re.search(r'\d+', submission.url).group(0)
                                            commenttext = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                        if re.search(ALIENWARE_URL_REGEX, submission.url):
                                            g_website = "alienware"
                                            commenttext = buildcommenttext_awa(AlienwareArena(submission.url, "new"), "new")
                                        if re.search(KEYHUB_URL_REGEX, submission.url):
                                            g_website = "keyhub"
                                            commenttext = buildcommenttext_keyhub(Keyhub(submission.url, "new"), "new")
                                        if re.search(GIVEECLUB_URL_REGEX, submission.url):
                                            g_website = "giveeclub"
                                            commenttext = buildcommenttext_giveeclub(GiveeClub(submission.url))
                                        if re.search(GLEAMIO_URL_REGEX, submission.url):
                                            g_website = "gleam"
                                            commenttext = buildcommenttext_gleam(Gleam(submission.url))
                                        if commenttext is not None and commenttext != "":
                                            commenttext += buildfootertext()
                                            if len(commenttext) < 10000:
                                                print('Commenting on post ' + str(submission) + ' after finding ' + g_website + ' domain', flush=True)
                                                submission.reply(body=commenttext)
                                                flair_text = submission.link_flair_text
                                                if commenttext.startswith("*Removed from Steam"):
                                                    if flair_text is None:
                                                        # flair post with delisted if no flair exists
                                                        submission.mod.flair(text="Delisted Game", css_class="DelistedGame", flair_template_id="9a5196c4-8865-11ec-8a1f-8261ed8ecd20")
                                                    elif "delisted" not in flair_text.lower():
                                                        # flair post with delisted if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = flair_text + " | Delisted Game"
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if g_website == "alienware" and commenttext is not None and commenttext != "":
                                                    tier_number = commenttext.split("Tier required: ")[1].split()[0]
                                                    if "Tier required: 1" not in commenttext and "* Keys available for all countries\n" not in commenttext:
                                                        # flair post with prior work required, regional issues and add tier
                                                        if flair_text is None:
                                                            # if no flair exists
                                                            new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues"
                                                            submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                        elif "prior work" not in flair_text.lower() and "regional" not in flair_text.lower():
                                                            # if not yet in flair
                                                            flair_id = submission.link_flair_template_id
                                                            new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues" + flair_text
                                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                        elif "regional" not in flair_text.lower():
                                                            # if regional not yet in flair
                                                            flair_id = submission.link_flair_template_id
                                                            new_text = "Tier " + tier_number + "+ | Regional Issues | " + flair_text
                                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                    if "Tier required: 1" not in commenttext and "* Keys available for all countries\n" in commenttext:
                                                        # flair post with prior work required and add tier
                                                        if flair_text is None:
                                                            # if no flair exists
                                                            new_text = "Tier " + tier_number + "+ | Prior Work Required"
                                                            submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                        elif "prior work" not in flair_text.lower():
                                                            # if not yet in flair
                                                            flair_id = submission.link_flair_template_id
                                                            new_text = "Tier " + tier_number + "+ | Prior Work Required | " + flair_text
                                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                    if "* Keys available for all countries\n" not in commenttext and "Tier required: 1" in commenttext:
                                                        # flair post with regional issues
                                                        if flair_text is None:
                                                            # if no flair exists
                                                            submission.mod.flair(text="Regional Issues", css_class="Regionlocked", flair_template_id="b3a089de-2437-11e6-8bda-0e93018c4773")
                                                        elif "regional" not in flair_text.lower():
                                                            # if not yet in flair
                                                            flair_id = submission.link_flair_template_id
                                                            new_text = flair_text + " | Regional Issues"
                                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if g_website == "keyhub" and commenttext is not None and commenttext != "":
                                                    flair_text = submission.link_flair_text
                                                    level_number = commenttext.split("Steam level required: ")[1].split()[0]
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        new_text = "Steam level " + level_number + "+"
                                                        submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                                    elif "level" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Steam level " + level_number + "+ | " + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if g_website == "giveeclub" and commenttext is not None and commenttext != "":
                                                    flair_text = submission.link_flair_text
                                                    level_number = commenttext.split("profile level on Steam")[0].split()[-1]
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        new_text = "Steam level " + level_number
                                                        submission.mod.flair(text=new_text, css_class="ReadComments",
                                                                             flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                                    elif "level" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Steam level " + level_number + " | " + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                                    # Set post as NSFW
                                                    submission.mod.nsfw()
                                elif (
                                    re.search(STEELSERIES_URL_REGEX, submission.url)
                                    or re.search(CRUCIAL_URL_REGEX, submission.url)
                                    or re.search(IGAMES_URL_REGEX, submission.url)
                                    or re.search(ALIENWARE_URL_REGEX, submission.url)
                                    or re.search(KEYHUB_URL_REGEX, submission.url)
                                    or re.search(GIVEECLUB_URL_REGEX, submission.url)
                                    or re.search(GLEAMIO_URL_REGEX, submission.url)
                                ):
                                    # Not found on steam-tracker, still post key availability part
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
                                        g_id = re.search(r'\d+', submission.url).group(0)
                                        commenttext = buildcommenttext_igames(iGames(g_id, g_website), "new")
                                    if re.search(ALIENWARE_URL_REGEX, submission.url):
                                        g_website = "alienware"
                                        commenttext = buildcommenttext_awa(AlienwareArena(submission.url, "new"), "new")
                                    if re.search(KEYHUB_URL_REGEX, submission.url):
                                        g_website = "keyhub"
                                        commenttext = buildcommenttext_keyhub(Keyhub(submission.url, "new"), "new")
                                    if re.search(GIVEECLUB_URL_REGEX, submission.url):
                                        g_website = "giveeclub"
                                        commenttext = buildcommenttext_giveeclub(GiveeClub(submission.url))
                                    if re.search(GLEAMIO_URL_REGEX, submission.url):
                                        g_website = "gleam"
                                        commenttext = buildcommenttext_gleam(Gleam(submission.url))
                                    if commenttext is not None and commenttext != "":
                                        commenttext += buildfootertext()
                                        if len(commenttext) < 10000:
                                            print('Commenting on post ' + str(submission) + ' after finding ' + g_website + ' domain', flush=True)
                                            submission.reply(body=commenttext)
                                            flair_text = submission.link_flair_text
                                            if g_website == "alienware" and commenttext is not None and commenttext != "":
                                                tier_number = commenttext.split("Tier required: ")[1].split()[0]
                                                if "Tier required: 1" not in commenttext and "* Keys available for all countries\n" not in commenttext:
                                                    # flair post with prior work required, regional issues and add tier
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues"
                                                        submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                    elif "prior work" not in flair_text.lower() and "regional" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues" + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                    elif "regional" not in flair_text.lower():
                                                        # if regional not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Tier " + tier_number + "+ | Regional Issues | " + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if "Tier required: 1" not in commenttext and "* Keys available for all countries\n" in commenttext:
                                                    # flair post with prior work required and add tier
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required"
                                                        submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                                    elif "prior work" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = "Tier " + tier_number + "+ | Prior Work Required | " + flair_text
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                                if "* Keys available for all countries\n" not in commenttext and "Tier required: 1" in commenttext:
                                                    # flair post with regional issues
                                                    if flair_text is None:
                                                        # if no flair exists
                                                        submission.mod.flair(text="Regional Issues", css_class="Regionlocked", flair_template_id="b3a089de-2437-11e6-8bda-0e93018c4773")
                                                    elif "regional" not in flair_text.lower():
                                                        # if not yet in flair
                                                        flair_id = submission.link_flair_template_id
                                                        new_text = flair_text + " | Regional Issues"
                                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if g_website == "keyhub" and commenttext is not None and commenttext != "":
                                                flair_text = submission.link_flair_text
                                                level_number = commenttext.split("Steam level required: ")[1].split()[0]
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Steam level " + level_number + "+"
                                                    submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                                elif "level" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Steam level " + level_number + "+ | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if g_website == "giveeclub" and commenttext is not None and commenttext != "":
                                                flair_text = submission.link_flair_text
                                                level_number = commenttext.split("profile level on Steam")[0].split()[-1]
                                                if flair_text is None:
                                                    # if no flair exists
                                                    new_text = "Steam level " + level_number
                                                    submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                                elif "level" not in flair_text.lower():
                                                    # if not yet in flair
                                                    flair_id = submission.link_flair_template_id
                                                    new_text = "Steam level " + level_number + " | " + flair_text
                                                    submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                                # Set post as NSFW
                                                submission.mod.nsfw()
                    elif re.search(INDIEGALA_TITLE_REGEX, submission.title, re.IGNORECASE) and re.search(INDIEGALA_URL_REGEX, submission.url):
                        title_split = re.split(INDIEGALA_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                        source_platform = "Indiegala"
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission) and game_name != "":
                            game = SteamSearchGame(game_name, False, "non-Steam")
                            if game.appid == 0:
                                game = SteamSearchGame(game_name, True, "non-Steam")
                            appid = game.appid
                            if appid != 0:
                                commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                if commenttext is not None and commenttext != "":
                                    commenttext += buildfootertext()
                                    if len(commenttext) < 10000:
                                        print('Commenting on post ' + str(submission) + ' after finding game ' + game_name, flush=True)
                                        submission.reply(body=commenttext)
                                        if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                            # Set post as NSFW
                                            submission.mod.nsfw()
                    elif re.search(EPIC_TITLE_REGEX, submission.title, re.IGNORECASE):
                        title_split = re.split(EPIC_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                        source_platform = "Epic"
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission) and game_name != "":
                            game = SteamSearchGame(game_name, False, "non-Steam")
                            if game.appid == 0:
                                game = SteamSearchGame(game_name, True, "non-Steam")
                            appid = game.appid
                            commenttext = buildcommenttext_epic(EpicGame(game_name))
                            if commenttext is not None and commenttext != "":
                                if appid != 0:
                                    steam_commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                    if steam_commenttext is not None and steam_commenttext != "":
                                        commenttext += steam_commenttext
                                commenttext += buildfootertext()
                            elif appid != 0:
                                steam_commenttext, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                                if steam_commenttext is not None and steam_commenttext != "":
                                    steam_commenttext += buildfootertext()
                                    commenttext = steam_commenttext
                            if commenttext is not None and commenttext != "" and len(commenttext) < 10000:
                                print('Commenting on post ' + str(submission) + ' after finding game ' + game_name, flush=True)
                                submission.reply(body=commenttext)
                                flair_text = submission.link_flair_text
                                if "*(NSFW)*" in commenttext and submission.over_18 is False:
                                    # Set post as NSFW
                                    submission.mod.nsfw()
                                if "* Blacklisted countries" in commenttext:
                                    # flair post with regional issues
                                    if flair_text is None:
                                        # if no flair exists
                                        submission.mod.flair(text="Regional Issues", css_class="Regionlocked", flair_template_id="b3a089de-2437-11e6-8bda-0e93018c4773")
                                    elif "regional" not in flair_text.lower():
                                        # if not yet in flair
                                        flair_id = submission.link_flair_template_id
                                        new_text = flair_text + " | Regional Issues"
                                        submission.mod.flair(text=new_text, flair_template_id=flair_id)
                    elif re.search(ALIENWARE_URL_REGEX, submission.url):
                        if fitscriteria(submission):
                            commenttext = buildcommenttext_awa(AlienwareArena(submission.url, "new"), "new")
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding Alienware Arena domain', flush=True)
                                    submission.reply(body=commenttext)
                                    flair_text = submission.link_flair_text
                                    if commenttext != "":
                                        tier_number = commenttext.split("Tier required: ")[1].split()[0]
                                        if "Tier required: 1" not in commenttext and "* Keys available for all countries\n" not in commenttext:
                                            # flair post with prior work required, regional issues and add tier
                                            if flair_text is None:
                                                # if no flair exists
                                                new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues"
                                                submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                            elif "prior work" not in flair_text.lower() and "regional" not in flair_text.lower():
                                                # if not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = "Tier " + tier_number + "+ | Prior Work Required | Regional Issues" + flair_text
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                            elif "regional" not in flair_text.lower():
                                                # if regional not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = "Tier " + tier_number + "+ | Regional Issues | " + flair_text
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                        if "Tier required: 1" not in commenttext and "* Keys available for all countries\n" in commenttext:
                                            # flair post with prior work required and add tier
                                            if flair_text is None:
                                                # if no flair exists
                                                new_text = "Tier " + tier_number + "+ | Prior Work Required"
                                                submission.mod.flair(text=new_text, css_class="restoften", flair_template_id="b204d6b4-0b90-11e4-9095-12313b0add52")
                                            elif "prior work" not in flair_text.lower():
                                                # if not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = "Tier " + tier_number + "+ | Prior Work Required | " + flair_text
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
                                        if "* Keys available for all countries\n" not in commenttext and "Tier required: 1" in commenttext:
                                            # flair post with regional issues
                                            if flair_text is None:
                                                # if no flair exists
                                                submission.mod.flair(text="Regional Issues", css_class="Regionlocked", flair_template_id="b3a089de-2437-11e6-8bda-0e93018c4773")
                                            elif "regional" not in flair_text.lower():
                                                # if not yet in flair
                                                flair_id = submission.link_flair_template_id
                                                new_text = flair_text + " | Regional Issues"
                                                submission.mod.flair(text=new_text, flair_template_id=flair_id)
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
                            g_id = re.search(r'\d+', submission.url).group(0)
                            commenttext = buildcommenttext_igames(iGames(g_id, g_website), "new")
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding ' + g_website + ' domain', flush=True)
                                    submission.reply(body=commenttext)
                    elif re.search(KEYHUB_URL_REGEX, submission.url):
                        if fitscriteria(submission):
                            commenttext = buildcommenttext_keyhub(Keyhub(submission.url, "new"), "new")
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding Keyhub domain', flush=True)
                                    submission.reply(body=commenttext)
                                    if commenttext is not None and commenttext != "":
                                        flair_text = submission.link_flair_text
                                        level_number = commenttext.split("Steam level required: ")[1].split()[0]
                                        if flair_text is None:
                                            # if no flair exists
                                            new_text = "Steam level " + level_number + "+"
                                            submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                        elif "level" not in flair_text.lower():
                                            # if not yet in flair
                                            flair_id = submission.link_flair_template_id
                                            new_text = "Steam level " + level_number + "+ | " + flair_text
                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
                    elif re.search(GOG_TITLE_REGEX, submission.title, re.IGNORECASE) or re.search(GOG_URL_REGEX, submission.url):
                        title_split = re.split(GOG_TITLE_REGEX, submission.title, flags=re.IGNORECASE)
                        game_name = title_split[-1].strip()
                        if fitscriteria(submission) and game_name != "":
                            gog_link = ""
                            if re.search(GOG_URL_REGEX, submission.url):
                                gog_link = re.split(re.search(GOG_URL_REGEX, submission.url).group(0), submission.url)[1].replace("/", "")
                            commenttext = buildcommenttext_gog(GOGGame(game_name, gog_link))
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding game ' + game_name, flush=True)
                                    submission.reply(body=commenttext)
                    elif re.search(GIVEECLUB_URL_REGEX, submission.url):
                        if fitscriteria(submission):
                            commenttext = buildcommenttext_giveeclub(GiveeClub(submission.url))
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding Giveeclub domain', flush=True)
                                    submission.reply(body=commenttext)
                                    if commenttext is not None and commenttext != "":
                                        flair_text = submission.link_flair_text
                                        level_number = commenttext.split("profile level on Steam")[0].split()[-1]
                                        if flair_text is None:
                                            # if no flair exists
                                            new_text = "Steam level " + level_number
                                            submission.mod.flair(text=new_text, css_class="ReadComments", flair_template_id="c7e83006-e1b5-11e4-b507-22000b2681f9")
                                        elif "level" not in flair_text.lower():
                                            # if not yet in flair
                                            flair_id = submission.link_flair_template_id
                                            new_text = "Steam level " + level_number + " | " + flair_text
                                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
                    elif re.search(GLEAMIO_URL_REGEX, submission.url):
                        if fitscriteria(submission):
                            commenttext = buildcommenttext_gleam(Gleam(submission.url))
                            if commenttext is not None and commenttext != "":
                                commenttext += buildfootertext()
                                if len(commenttext) < 10000:
                                    print('Commenting on post ' + str(submission) + ' after finding Gleam domain', flush=True)
                                    submission.reply(body=commenttext)
                    if re.search(RANDOM_TITLE_REGEX, submission.title, re.IGNORECASE):
                        flair_text = submission.link_flair_text
                        if flair_text is None:
                            # if no flair exists
                            new_text = "Random"
                            submission.mod.flair(text=new_text, css_class="itchio", flair_template_id="2e9be5ce-8121-11ec-97f5-ae0ba3b1ee73")
                        elif "random" not in flair_text.lower():
                            # if not yet in flair
                            flair_id = submission.link_flair_template_id
                            new_text = flair_text + " | Random"
                            submission.mod.flair(text=new_text, flair_template_id=flair_id)
            except PrawcoreException:
                print('Trying to reach Reddit', flush=True)
                time.sleep(30)


class CommentWatch(threading.Thread):
    def run(self):
        print('Watching all comments on: ' + SUBLIST)
        while True:
            try:
                for comment in reddit.subreddit(SUBLIST).stream.comments():
                    test_comment_gleamio = re.search(GLEAMIO_URL_REGEX, comment.body, re.IGNORECASE)
                    test_comment_steam = re.search(STEAM_APPURL_REGEX, comment.body, re.IGNORECASE)
                    if test_comment_gleamio:
                        if comment.approved_by is None:
                            comment.mod.approve()
                        gleam_links = []
                        urlregex = re.finditer(GLEAMIO_URL_REGEX, comment.body)
                        for url in urlregex:
                            gleam_links.append(url.group(0))
                        # remove duplicates
                        gleam_links = list(dict.fromkeys(gleam_links))
                        commenttext = ""
                        for url in range(len(gleam_links)):
                            make_comment = buildcommenttext_gleam(Gleam(url))
                            if make_comment is not None and make_comment != "":
                                commenttext += make_comment
                        if commenttext != "":
                            commenttext += buildfootertext()
                            if len(commenttext) < 10000:
                                print('Replying to comment ' + str(comment) + ' after finding Gleam domain', flush=True)
                                comment.reply(commenttext)
                    test_comment_expired_words = ['expired', 'ended']
                    test_comment_expired_phrases = ['attention this giveaway has ended', 'this reward has ended', 'this giveaway has ended']
                    # Remove punctuation
                    comment_expired = re.compile(r'[^\w\s]').sub('', comment.body.lower())
                    # Check if the comment contains one of the expired words or matches one of the phrases
                    if len(comment_expired.split()) <= 3 and any(word in comment_expired.split() for word in test_comment_expired_words) or any(phrase in comment_expired for phrase in test_comment_expired_phrases):
                        # Report the post as expired
                        comment.submission.report(reason='Expired')
                    if comment.banned_by is not None:
                        continue
                    if test_comment_steam and fitscriteria(comment):
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
                        if not re.search(STEAM_PLATFORM_REGEX, comment.submission.title, re.IGNORECASE):
                            source_platform = "nonSteam"
                        for i in range(len(games)):
                            appid = re.search(r'\d+', games[i]).group(0)
                            make_comment, javascripttext = buildcommenttext(SteamGame(appid), False, source_platform)
                            if make_comment is not None and make_comment != "":
                                commenttext += make_comment
                                appids.append(appid)
                            if javascripttext is not None and javascripttext != "":
                                javascripts.append(javascripttext)
                        if commenttext != "":
                            commenttext += buildfootertext()
                            if len(commenttext) < 10000:
                                print('Replying to comment ' + str(comment) + ' after finding game ' + ', '.join(appids), flush=True)
                                botcomment = comment.reply(commenttext)
                                if len(javascripts) > 0:
                                    for text in javascripts:
                                        botcomment.reply(text)
            except PrawcoreException:
                print('Trying to reach Reddit', flush=True)
                time.sleep(30)


class EditCommentWatch(threading.Thread):
    def run(self):
        print('Watching bot comments')
        while True:
            try:
                comments = []
                for comment in reddit.redditor(BOT_USERNAME).comments.new(limit=20):
                    now = time.time()
                    age = now - comment.created_utc  # in seconds
                    if comment.banned_by is None and age <= 14400 and comment.body.startswith('**Giveaway details**') and "* Available keys: 0\n" not in comment.body:
                        comments.append(comment)
                if len(comments) > 0:
                    seconds = 60
                    if len(comments) > 10:
                        seconds = 120
                    sleep_time = seconds / len(comments)
                    for comment in comments:
                        g_website = ""
                        submission_url = comment.submission.url
                        if re.search(ALIENWARE_URL_REGEX, submission_url):
                            g_website = "alienware"
                            split_part = "* No keys for:"
                        elif re.search(STEELSERIES_URL_REGEX, submission_url):
                            g_website = "steelseries"
                            split_part = "\n* Total keys:"
                        elif re.search(CRUCIAL_URL_REGEX, submission_url):
                            g_website = "crucial"
                            split_part = "\n* Total keys:"
                        elif re.search(IGAMES_URL_REGEX, submission_url):
                            g_website = "igames"
                            split_part = "\n* Total keys:"
                        elif re.search(KEYHUB_URL_REGEX, submission_url):
                            g_website = "keyhub"
                            split_part = "* Steam level required:"
                        if g_website == "alienware":
                            edited_part = buildcommenttext_awa(AlienwareArena(comment.submission.url, "update"), "update")
                        elif g_website in ["steelseries", "crucial", "igames"]:
                            g_id = re.search(r'\d+', comment.submission.url).group(0)
                            edited_part = buildcommenttext_igames(iGames(g_id, g_website), "update")
                        elif g_website == "keyhub":
                            edited_part = buildcommenttext_keyhub(Keyhub(comment.submission.url, "update"), "update")
                        else:
                            continue
                        original_body = comment.body
                        original_body_split = original_body.split("**Giveaway details**\n\n")
                        split_test = original_body_split[1].split(split_part, 1)
                        if len(split_test) != 1 and len(split_test) != 2:
                            continue
                        part_to_edit = split_test[0]
                        if g_website == "alienware" and len(split_test) == 1:
                            split_part = "* Keys available for"
                            split_test = original_body_split[1].split(split_part, 1)
                        if g_website in ["steelseries", "crucial", "igames"]:
                            test_out_of_keys = re.sub("[^0-9]", "", part_to_edit)
                            if test_out_of_keys.startswith('0'):
                                # prevents edits on a restock, leads to incorrect keys
                                edited_part = part_to_edit
                        if g_website == "alienware":
                            try:
                                if "Tier required: 0" in edited_part and "Tier required: 0" not in part_to_edit:
                                    original_tier_split = part_to_edit.split("Tier required")
                                    original_tier_split_2 = original_tier_split[1].split(split_part)
                                    zero_tier_split = edited_part.split("Tier required")
                                    edited_part = zero_tier_split[0] + "Tier required" + original_tier_split_2[0]
                            except TypeError:
                                continue
                        original_body_part = split_test[1]
                        edited_comment = ""
                        if edited_part != part_to_edit:
                            try:
                                edited_comment = "**Giveaway details**\n\n" + edited_part + split_part + original_body_part
                            except TypeError:
                                continue
                            if len(edited_comment) < 10000:
                                if "Available keys: 0\n" in edited_part:
                                    # flair post as expired, replace update text with runtime
                                    comment.submission.mod.flair(text="Expired", css_class="Expired", flair_template_id="3f44a048-da47-11e3-8cba-12313d051ab0")
                                    age = time.time() - comment.submission.created_utc  # in seconds
                                    if "\n*Updating available keys every minute*\n" in edited_comment:
                                        expire_time = "\n*Giveaway lasted for " + format_timespan(int(age), max_units=2) + "*\n"
                                        edited_comment = edited_comment.replace("\n*Updating available keys every minute*\n", expire_time)
                                comment.edit(body=edited_comment)
                        # try edit(s) every minute
                        time.sleep(sleep_time)
            except PrawcoreException:
                print('Trying to reach Reddit', flush=True)
                time.sleep(30)


class EditCommentWatchLong(threading.Thread):
    def run(self):
        print('Watching longlasting bot comments')
        while True:
            try:
                comments = []
                for comment in reddit.redditor(BOT_USERNAME).comments.new(limit=100):
                    now = time.time()
                    age = now - comment.created_utc  # in seconds
                    if comment.banned_by is None and age > 14400 and comment.body.startswith('**Giveaway details**') and "* Available keys: 0\n" not in comment.body:
                        comments.append(comment)
                if len(comments) > 0:
                    seconds = 1800
                    if len(comments) > 10:
                        seconds = 3600
                    sleep_time = seconds / len(comments)
                    for comment in comments:
                        g_website = ""
                        submission_url = comment.submission.url
                        if re.search(ALIENWARE_URL_REGEX, submission_url):
                            g_website = "alienware"
                            split_part = "* No keys for:"
                        elif re.search(STEELSERIES_URL_REGEX, submission_url):
                            g_website = "steelseries"
                            split_part = "\n* Total keys:"
                        elif re.search(CRUCIAL_URL_REGEX, submission_url):
                            g_website = "crucial"
                            split_part = "\n* Total keys:"
                        elif re.search(IGAMES_URL_REGEX, submission_url):
                            g_website = "igames"
                            split_part = "\n* Total keys:"
                        elif re.search(KEYHUB_URL_REGEX, submission_url):
                            g_website = "keyhub"
                            split_part = "* Steam level required:"
                        if g_website == "alienware":
                            edited_part = buildcommenttext_awa(AlienwareArena(comment.submission.url, "update"), "update")
                        elif g_website in ["steelseries", "crucial", "igames"]:
                            g_id = re.search(r'\d+', comment.submission.url).group(0)
                            edited_part = buildcommenttext_igames(iGames(g_id, g_website), "update")
                        elif g_website == "keyhub":
                            edited_part = buildcommenttext_keyhub(Keyhub(comment.submission.url, "update"), "update")
                        else:
                            continue
                        original_body = comment.body
                        original_body_split = original_body.split("**Giveaway details**\n\n")
                        split_test = original_body_split[1].split(split_part, 1)
                        if len(split_test) != 1 and len(split_test) != 2:
                            continue
                        part_to_edit = split_test[0]
                        if g_website == "alienware" and len(split_test) == 1:
                            split_part = "* Keys available for"
                            split_test = original_body_split[1].split(split_part, 1)
                        if g_website in ["steelseries", "crucial", "igames"]:
                            test_out_of_keys = re.sub("[^0-9]", "", part_to_edit)
                            if test_out_of_keys.startswith('0'):
                                # prevents edits on a restock, leads to incorrect keys
                                edited_part = part_to_edit
                        if g_website == "alienware":
                            try:
                                if "Tier required: 0" in edited_part and "Tier required: 0" not in part_to_edit:
                                    original_tier_split = part_to_edit.split("Tier required")
                                    original_tier_split_2 = original_tier_split[1].split(split_part)
                                    zero_tier_split = edited_part.split("Tier required")
                                    edited_part = zero_tier_split[0] + "Tier required" + original_tier_split_2[0]
                            except TypeError:
                                continue
                        original_body_part = split_test[1]
                        edited_comment = ""
                        if edited_part != part_to_edit:
                            try:
                                edited_comment = "**Giveaway details**\n\n" + edited_part + split_part + original_body_part.replace("available keys every minute", "available keys every 30 minutes")
                            except TypeError:
                                continue
                            if len(edited_comment) < 10000:
                                if "Available keys: 0\n" in edited_part:
                                    # flair post as expired, replace update text with runtime
                                    comment.submission.mod.flair(text="Expired", css_class="Expired", flair_template_id="3f44a048-da47-11e3-8cba-12313d051ab0")
                                    age = time.time() - comment.submission.created_utc  # in seconds
                                    if "\n*Updating available keys every 30 minutes*\n" in edited_comment:
                                        expire_time = "\n*Giveaway lasted for " + format_timespan(int(age), max_units=2) + "*\n"
                                        edited_comment = edited_comment.replace("\n*Updating available keys every 30 minutes*\n", expire_time)
                                comment.edit(body=edited_comment)
                        # try edit(s) every 30 minutes
                        time.sleep(sleep_time)
            except PrawcoreException:
                print('Trying to reach Reddit', flush=True)
                time.sleep(30)


class RepostWatch(threading.Thread):
    def run(self):
        print('Started watching subs for reposts: ' + SUBLIST)
        subreddit = reddit.subreddit(SUBLIST)
        while True:
            try:
                for submission in subreddit.stream.submissions(skip_existing=True):
                    if submission.banned_by is not None:
                        continue
                    if repostwatch_title(submission.title) and repostwatch_duplicate(submission):
                        commenttext = buildcommenttext_repost(submission)
                        submission.mod.remove(spam=True)
                        comment = submission.reply(body=commenttext)
                        comment.mod.distinguish(sticky=True)
            except PrawcoreException:
                print('Trying to reach Reddit', flush=True)
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
    repostwatch = RepostWatch()

    subwatch.start()
    commentwatch.start()
    editcommentwatch.start()
    editcommentwatchlong.start()
    repostwatch.start()
