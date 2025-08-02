# FGF_Info_Bot

Bot for Reddit that comments on [r/FreeGameFindings](https://www.reddit.com/r/FreeGameFindings) with detailed game and giveaway information on posts linking to Steam, GOG, or Epic Games.

## Table of Contents

- [Features](#rocket-features)
- [How It Works](#wrench-how-it-works)
- [Information Provided](#book-information-provided)
- [Giveaway details](#gift-giveaway-details)
- [Contributing](#handshake-contributing)

## :rocket: Features

This is an original bot expanded upon specifically for [r/FreeGameFindings](https://www.reddit.com/r/FreeGameFindings).
It currently supports:

- **Steam Store** and **SteamDB** submissions
- **GOG** submissions
- **IndieGala** submissions
- **Epic Games Store** submissions, including instant checkout links for all platforms (PC, Android and iOS)
- All work with FreeGameFindings title format, by searching for the game/dlc on Steam
- Also works for games/dlc removed from Steam, by searching for them on [archive.org/web](https://archive.org/web)
- Additionally provides giveaway information for **Alienware Arena**, **SteelSeries**, **Crucial**, **iGames**, **KeyHub**, **GiveeClub** and **Gleam** giveaways
- Flair automation for posts (e.g., marking expired, delisted or region-locked offers)

## :wrench: How It Works

The bot handles a wide variety of submission types. Here's how it interprets each one:

1. **Steam Store Submission**  
   Pulls data directly from the linked store page.
2. **SteamDB submission**  
   Converts app ID into a Steam store URL to retrieve data.
3. **Other Steam-related or IndieGala submission**  
   Get the game/dlc name from the submission title, search the Steam store with it and get data from the correct store link from the search results
4. **Delisted or removed**  
   Uses [steam-tracker](https://steam-tracker.com/) and [archive.org](https://archive.org/web) to find data:
   - Delisted: get the Steam store link using the appid found on steam-tracker
   - Removed: search archive.org for the most recent archived store link
5. **Alienware Arena**  
   Retrieve details of Alienware Arena giveaways, based on [awa_key_checker](https://github.com/Saulios/awa_key_checker). Details include account level required, initial key amount and country/continent restrictions.
6. **SteelSeries/Crucial/iGames**  
   Retrieve key availability from the website API
7. **Keyhub**  
   Retrieve key availability from the website API and Steam level requirement from the giveaway link
8. **GiveeClub**  
   Retrieve tasks from the giveaway link
9. **Gleam**  
   Retrieve tasks, required accounts and ASF commands for Steam games from the giveaway link
10. **GOG**  
   Use either the submission link or the title to look up details in the GOG API
11. **Epic Games**  
    Searches the Epic Store via its API and adds instant checkout links for all platforms. Adds Steam game data if available.

## :book: Information Provided

Below is a comparison of what kind of information the bot provides based on the source or platform.


|                |  Steam   | Removed from Steam | Unreleased on Steam | Steam link in non-steam submission |   GOG    |   Epic   |
|----------------|:--------:|:------------------:|:-------------------:|:----------------------------------:|:--------:|:--------:|
| Links          | &#10004; |      &#10004;      |      &#10004;       |              &#10004;              | &#10004; | &#10004; |
| Reviews        | &#10004; |      &#10004;      |      &#10060;       |              &#10004;              | &#10004; | &#10004; |
| Description    | &#10004; |      &#10004;      |      &#10004;       |              &#10004;              | &#10004; | &#10004; |
| Price          | &#10004; |      &#10060;      |      &#10004;       |              &#10004;              | &#10060; | &#10004; |
| Release Date   | &#10004; |      &#10004;      |      &#10004;       |              &#10004;              | &#10004; | &#10004; |
| Developers     | &#10004; |      &#10004;      |      &#10004;       |              &#10004;              | &#10004; | &#10004; |
| Genre/Tags     | &#10004; |      &#10004;      |      &#10004;       |              &#10004;              | &#10004; | &#10004; |
| Achievements   | &#10004; |      &#10004;      |      &#10060;       |              &#10060;              | &#10004; | &#10060; |
| Trading Cards  | &#10004; |      &#10004;      |      &#10060;       |              &#10060;              | &#10060; | &#10060; |
| Game Count     | &#10004; |      &#10004;      |      &#10004;       |              &#10060;              | &#10060; | &#10060; |
| ASF/addlicense | &#10004; |      &#10060;      |      &#10060;       |              &#10060;              | &#10060; | &#10060; |

## :gift: Giveaway details

Giveaway details vary by website. Available keys is updated automatically every minute in the bot comment:


|                   | Alienware Arena | SteelSeries | Crucial  |  iGames  |  Keyhub  |
|-------------------|:---------------:|:-----------:|:--------:|:--------:|:--------:|
| Available keys    |    &#10004;     |  &#10004;   | &#10004; | &#10004; | &#10004; |
| Total keys        |    &#10004;     |  &#10004;   | &#10004; | &#10004; | &#10004; |
| Level requirement |    &#10004;     |  &#10060;   | &#10060; | &#10060; | &#10004; |
| Regional issues   |    &#10004;     |  &#10060;   | &#10060; | &#10060; | &#10060; |

## :handshake: Contributing

Want to help improve the bot? Contributions are welcome!

Please fork the repository, create a new branch for your feature or bugfix, and submit a pull request.
