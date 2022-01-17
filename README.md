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

## What information does the bot provide?

|                |  Steam  | Removed Steam | Epic/Indiegala |
|:--------------:|:-------:|:-------------:|:--------------:|
|      Links     | &#9745; |    &#9745;    |     &#9745;    |
|     Reviews    | &#9745; |    &#9745;    |     &#9745;    |
|   Description  | &#9745; |    &#9745;    |     &#9745;    |
|      Price     | &#9745; |    &#9744;    |     &#9745;    |
|  Release Date  | &#9745; |    &#9745;    |     &#9745;    |
|   Genre/Tags   | &#9745; |    &#9745;    |     &#9745;    |
|  Achievements  | &#9745; |    &#9745;    |     &#9744;    |
|  Trading Cards | &#9745; |    &#9745;    |     &#9744;    |
|   Game Count   | &#9745; |    &#9745;    |     &#9744;    |
| ASF/addlicense | &#9745; |    &#9744;    |     &#9744;    |
