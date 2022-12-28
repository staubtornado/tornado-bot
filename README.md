## What is TornadoBot?
The TornadoBot is a Discord bot, that aims to replace MEE6 and other bots that are used for moderation and fun. 
It is written in Python 3.11 and uses the Py-Cord library. It is currently in development, but updates will be released 
frequently in order to make it as good as possible.

---

## What is the purpose of this project?
The purpose of this project is to create an open-source alternative to popular bots like MEE6, Dyno, and others.
It is designed to be used by anyone, therefore the installation process is very simple and easy to follow.

---

## What can I promise?
No NFTs, open-source forever, no ads, and no data-selling.
Premium features will be available for free on self-hosted instances of the bot, but will be paid for on the official 
bot. Features will be added frequently, and the bot will be updated frequently.

---

## How do I install TornadoBot?
 1. [Download the latest release](https://github.com/staubtornado/tornado-bot/releases) or clone the repository if you 
    want to use the development version.
 2. Make sure the directory is not a zip file. If it is, extract it.
 3. Install the newest version of [Python 3.11](https://www.python.org/downloads/).
 4. Create a new file called `.env` in `/data/config/` and paste in the following lines:

    ####
        DISCORD_BOT_TOKEN = your token from the discord developer portal
        SPOTIFY_CLIENT_ID = client id from the Spotify developer portal
        SPOTIFY_CLIENT_SECRET = client secret from the Spotify developer portal
        LYRICS_FIND_ACCESS_TOKEN = token for the lyricsfind API

 5. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications) and paste in 
the token.
 6. Create an application in the [Spotify Developer Portal](https://developer.spotify.com/dashboard/) and paste in the 
client id and client secret.
7. Create an account on the [LyricsFind API](https://lyricsfind.com/) and paste in the access token.
8. Save the `.env` file.

#### Windows:
1. Run start.bat.
2. Wait for the script to check the dependencies.
3. That's it!

#### Linux:
1. Install or update to the newest version of Python 3.11.
2. Run `python3.11 -m pip install -r requirements.txt` in the root directory.
3. Run `python3.11 main.py` in the root directory.

---

## What features does the bot have?
- Music (Spotify, YouTube, SoundCloud, and more)
- Moderation
- Auto-moderation
- Fun commands
- Utility commands
- And more!
- Premium features (coming later 2023)
  ### Read the documentation for more information.
  (It is currently being written)

---

## What needs to be done?
- [ ] Add games to the bot.
  - Ideas:
    - [ ] Connect 4
    - [ ] Tic Tac Toe
    - [ ] Hangman
    - [ ] Chess
    - [ ] Number Guessing
    - [ ] Rock Paper Scissors
    - [ ] Geoguessr
- [ ] Add a working API to the bot.
- [ ] Add a website to the bot (requires API).
- [ ] Add an update system to the bot.
- [ ] Improve stability of the bot.
- [ ] Improve the auto-moderation system.
- [ ] Improve the music search system.
- [ ] Add multiple languages to the bot. 

---

## Why is the development process so slow?
The bot needs to be able to work on Linux and Windows and is currently only developed by a single person.

---

## How can I help?
Feel free to contribute to the bots' development. This would help the project a lot.

######

Requirements:
   - Understanding of Python 3.11
   - Understanding of SQL
   - Understanding of Py-Cord
   - Understanding of asynchronous programming