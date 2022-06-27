# RedditSteamGameInfo
Bot for Reddit that comments on submissions if they link to Steam games

Original bot modified specifically for r/FreeGameFindings, with added functionality:
- Works for SteamDB submissions
- Works with FreeGameFindings title format by searching for the game/dlc on Steam
- Works for games/dlc removed from Steam by searching for them on [archive.org/web](https://archive.org/web)
- Provides giveaway details for Alienware Arena, SteelSeries, Crucial and iGames
- Add or edit submission flairs in certain situations (expired giveaway, delisted game)

## Workflows

1. **Steam store submission**: Take all details directly from the submission link
2. **SteamDB submission**: Take the appid from the submission link to get the Steam store link
3. **Other Steam or non-Steam submission**: Get the game/dlc name from the submission title, search the Steam store with it and get the correct store link from the results
4. **Delisted or removed**: Get the game/dlc name from the submission title, use [steam-tracker](https://steam-tracker.com/) to find the appid
    - Delisted: get the Steam store link using the appid
    - Removed: search [archive.org/web](https://archive.org/web) for the most recent archived store link and get details from there
5. **Alienware Arena**: Retrieve details of Alienware Arena giveaways, based on [awa_key_checker](https://github.com/Saulios/awa_key_checker). Details include account level required, initial key amount and country/continent restrictions.
6. **SteelSeries/Crucial/iGames**: Retrieve key availability from the website API
7. **Keyhub**: Retrieve key availability from the website API and Steam level requirement from the giveaway link

## What information will the bot provide?

### Game/DLC details
|                |   Steam  | Removed from Steam | Unreleased on Steam | Non-Steam |
|:--------------:|:--------:|:------------------:|:-------------------:|:---------:|
|      Links     | &#10004; |      &#10004;      |       &#10004;      |  &#10004; |
|     Reviews    | &#10004; |      &#10004;      |       &#10060;      |  &#10004; |
|   Description  | &#10004; |      &#10004;      |       &#10004;      |  &#10004; |
|      Price     | &#10004; |      &#10060;      |       &#10004;      |  &#10004; |
|  Release Date  | &#10004; |      &#10004;      |       &#10004;      |  &#10004; |
|   Genre/Tags   | &#10004; |      &#10004;      |       &#10004;      |  &#10004; |
|  Achievements  | &#10004; |      &#10004;      |       &#10060;      |  &#10060; |
|  Trading Cards | &#10004; |      &#10004;      |       &#10060;      |  &#10060; |
|   Game Count   | &#10004; |      &#10004;      |       &#10004;      |  &#10060; |
| ASF/addlicense | &#10004; |      &#10060;      |       &#10060;      |  &#10060; |

### Giveaway details
|                   | Alienware Arena | SteelSeries |  Crucial |  iGames  |  Keyhub  |
|:-----------------:|:---------------:|:-----------:|:--------:|:--------:|:--------:|
|   Available keys  |     &#10004;    |   &#10004;  | &#10004; | &#10004; | &#10004; |
|     Total keys    |     &#10004;    |   &#10004;  | &#10004; | &#10004; | &#10004; |
| Level requirement |     &#10004;    |   &#10060;  | &#10060; | &#10060; | &#10004; |
|  Regional issues  |     &#10004;    |   &#10060;  | &#10060; | &#10060; | &#10060; |
