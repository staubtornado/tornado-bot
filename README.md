## What is TornadoBot?
Tornado-bot is a discord bot build in python 3.8 that is designed to be a simple and easy to use bot. It makes use of 
the newest discord API features and is built on top of the Py-Cord (discord.py fork) library.

---

## What is the purpose of this project?
The goal of this project is to create an open-source discord bot that has the capability to compete with other bots like
MEE6, Dank Memer, or Dyno.

---

## How do I install TornadoBot?
 1. [Download the latest release](https://github.com/staubtornado/tornado-bot/releases) or clone the repository if you want to use the development version.
 2. Install Python 3.8
 3. Install all the dependencies 
    - pip install -r requirements.txt
    - install selenium drivers for chrome, Firefox, or edge
    - install ffmpeg
 4. Create a bot in the discord developer portal
 5. Create an application in the Spotify developer portal
 6. Create a `.env` file in `./data/config` and paste in the following information:

    #####

        DISCORD_BOT_TOKEN = your token from the discord developer portal
        SPOTIFY_CLIENT_ID = client id from the Spotify developer portal
        SPOTIFY_CLIENT_SECRET = client secret from the Spotify developer portal
 7. Save your `.env` file
 8. Run the bot with `main.py` file in the root directory  

---

## What features does the bot have?
The bot has the following features:
- Music
    - The bot can play music in a voice channel from various sources like YouTube, SoundCloud, and Spotify. With the 
  help of the Spotify API, the bot can also play music from Spotify playlists **|** artists **|** albums. 
    - **[/]** `play [song name | link | Preset]`
    - **[/]** `pause` Pauses the music
    - **[/]** `resume` Resumes the music
    - **[/]** `stop` Stops the music and clears the queue
    - **[/]** `skip [force]` Skips the current song or forces the bot to skip the current song if a DJ uses force 
                              parameter
    - **[/]** `queue [page]` Shows the queue with ten songs per page.
    - **[/]** `clear` Clears the queue
    - **[/]** `remove [index]` Removes a song from the queue
    - **[/]** `shuffle` Shuffles the queue
    - **[/]** `volume [percent]` Sets the volume to the specified volume of the current song.
    - **[/]** `loop` Sets the looping of the current song to on or off.
    - **[/]** `now` Shows the current song that is playing.
    - **[/]** `reverse` Reverses the current queue.
    - **[/]** `join` Joins the bot to the voice channel.
    - **[/]** `leave` Leaves the bot from the voice channel.
    - **[/]** `summon` Joins the bot to the voice channel.

#####

- Images
    - The bot can scrape images from various sources. This is done via Selenium to support JavaScript rendered websites.
    - **[/]** `images [category]` Scrapes a random image by the given category from the web.

#####

- Experience
  - This is a level system for guilds that works like the one from MEE6. 
  - **[/]** `leaderboard [page]` Sends a page of the leaderboard.
  - **[/]** `rank [user]` Sends the rank of the user.

####

- Economy (Not finished)
  - Everyone can claim coins everyday on every server the bot is in. They can trade, buy text or voice channels and 
    roles. Server owner earn coins by fees on transactions on their servers.
  - **[/]** `wallet [user]` Shows information about the users' wallet.
  - **[/]** `transfer [amount] [user]` Transfer coins to another users' wallet.
  - **[/]** `buy [subject]` Buy text or voice channel and roles, that are sold by other users.
  - **[/]** `sell [subject] [price]` Sell an object you own to someone.
  - **[/]** `claim [Daily | Monthly | Special]` Claim available coins or prices.

####

- Utilities (Not finished)
  - **[/]** `ban [user] [reason]` Bans a user from the guild and tells them the reason.
  - **[/]** `unban [user]` Unbans a user from the guild.

---

## What needs to be done?
- [ ] Add image processing commands
- [ ] Make music streaming more efficient and more stable
- [ ] Add premium and beta functionality
- [ ] Add auto updates
- [ ] Add a ticket system
- [x] Only display NSFW commands in NSFW channels (While they do not work in non-NSFW channels, they should still not 
      be displayed there)
- [ ] Add a command to get the bot's uptime
- [ ] Add a command to get the bot's ping
- [x] Add a welcome message to the bot
- [ ] Add server specific settings
- [ ] Add a help command
- [ ] Add games to the bot
- [ ] Add multiple languages to the bot
- [ ] Create a requirements.txt file
- [ ] Improve SQL so it can add missing columns
- [ ] Add economy system

---

## Why is the development process so slow?
The bot needs to be able to work on Linux and Windows and is currently only developed by a single person.

---

## How can I help?
Feel free to contribute to the bot's development. This would help the project a lot.

######

Requirements:
   - A GitHub account
   - A Discord account
   - A PC or laptop
   - A good understanding of Python, Selenium, SQL and Discord.py