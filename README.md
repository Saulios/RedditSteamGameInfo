# RedditSteamGameInfo
Bot for Reddit that comments on submissions if they link to Steam games

Original bot modified specifically for r/FreeGameFindings, with added functionality:
- Works for SteamDB submissions
- Works with FGF title format by searching for the game/dlc on Steam
- Works for games/dlc removed from Steam by searching for them on [archive.org/web](https://archive.org/web)

## Workflows

1. **Steam store submission**: Take all details directly from the submission link
2. **SteamDB submission**: Take the appid from the submission link to get the Steam store link
3. **Other Steam or non-Steam (Indiegala/Epic) submission**: Get the game/dlc name from the submission title, search the Steam store with it and get the correct store link from the results
4. **Delisted or removed**: Get the game/dlc name from the submission title, use either [madjoki](https://steam.madjoki.com/apps/banned) or [steam-tracker](https://steam-tracker.com/) to find the appid (note: I can't use SteamDB)
    - Delisted: get the Steam store link using the appid
    - Removed: search [archive.org/web](https://archive.org/web) for the most recent archived store link and get details from there

## What information will the bot provide?

|                |   Steam  | Removed from Steam | Unreleased on Steam | Epic/Indiegala |
|:--------------:|:--------:|:------------------:|:-------------------:|:--------------:|
|      Links     | &#10004; |      &#10004;      |       &#10004;      |    &#10004;    |
|     Reviews    | &#10004; |      &#10004;      |       &#10060;      |    &#10004;    |
|   Description  | &#10004; |      &#10004;      |       &#10004;      |    &#10004;    |
|      Price     | &#10004; |      &#10060;      |       &#10004;      |    &#10004;    |
|  Release Date  | &#10004; |      &#10004;      |       &#10004;      |    &#10004;    |
|   Genre/Tags   | &#10004; |      &#10004;      |       &#10004;      |    &#10004;    |
|  Achievements  | &#10004; |      &#10004;      |       &#10060;      |    &#10060;    |
|  Trading Cards | &#10004; |      &#10004;      |       &#10060;      |    &#10060;    |
|   Game Count   | &#10004; |      &#10004;      |       &#10004;      |    &#10060;    |
| ASF/addlicense | &#10004; |      &#10060;      |       &#10060;      |    &#10060;    |
