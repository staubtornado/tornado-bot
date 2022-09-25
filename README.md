## What is TornadoBot?
Tornado-bot is a discord bot build in python 3.10 that is designed to be a simple and easy to use bot. It makes use of 
the newest discord API features and is built on top of the Py-Cord (discord.py fork) library.

---

## What is the purpose of this project?
The goal of this project is to create an open-source discord bot that has the capability to compete with other bots like
MEE6, Dank Memer, or Dyno.

---

## How do I install TornadoBot?
 1. [Download the latest release](https://github.com/staubtornado/tornado-bot/releases) or clone the repository if you 
    want to use the development version.
 2. Install the newest Python 3.10
 3. Install all the dependencies 
    - pip install -r requirements.txt
    - install ffmpeg
 4. Create a bot in the discord developer portal
 5. Create an application in the Spotify developer portal
 6. Create a `.env` file in `./data/config` and paste in the following information:

    #####
        DISCORD_BOT_TOKEN = your token from the discord developer portal
        SPOTIFY_CLIENT_ID = client id from the Spotify developer portal
        SPOTIFY_CLIENT_SECRET = client secret from the Spotify developer portal
        LYRICS_FIND_ACCESS_TOKEN = token for the lyricsfind API
 7. Save your `.env` file
 8. Run the bot with `main.py` or (Recommended) `start.bat` if you are on Windows.  

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
    - **[/]** `summon [voice channel]` Joins the bot to the voice channel.
    - **[/]** `lyrics [song] [artist]` Search for the lyrics of the current song or by name and artist.
    - **[/]** `session` Control with [BetterMusicControl](https://github.com/staubtornado/BetterMusicControl/releases)
                        the music without leaving your game. Hotkeys everywhere!
    - **[/]** `next [search]` Adds a song to the priority queue.
#####

- Images
    - The bot can scrape images from all subreddits.
    - **[/]** `images [category]` Scrapes a random image by the given category from Reddit.

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
  - **[/]** `claim [daily | work | special]` Claim available coins or prices.
  - **[/]** `work` Start working and claim your payment after oe hour.
  - **[/]** `wallstreet` Check out the latest stock prices.

####

- Utilities (Not finished)
  - **[/]** `ban [user] [reason]` Bans a user from the guild and tells them the reason.
  - **[/]** `unban [user]` Unbans a user from the guild.
  - **[/]** `purge [amount] [ignore: user]` Deletes an amount of messages in a channel.
  - **[/]** `kick [user] [reason]` Kick a user from a guild.

####

- Settings (Not finished)
  - **[/]** `settings music [embed size: (Small | Medium | Large) | update embed: (True | False)]` 
             Configure the music player.
  - **[/]** `settings experience [enabled (true | false) | multiplier (1 - 5)]` Configure the leveling.
  - **[/]** `settings tickets voice [True | False]` Enable or disable the creation of a voice channel for each ticket.
  - **[/]** `settings tickets category [category: CategoryChannel]` Change where new tickets are created.

---

## What needs to be done?
- [ ] Add more image processing commands
- [ ] Make music streaming more efficient and more stable
- [x] Add premium and beta functionality
- [ ] Add auto updates
- [ ] Add a ticket system
- [x] Only display NSFW commands in NSFW channels (While they do not work in non-NSFW channels, they should still not 
      be displayed there)
- [x] Add a command to get the bot's uptime
- [x] Add a command to get the bot's ping
- [x] Add a welcome message to the bot
- [x] Add server specific settings
- [x] Add a help command
- [ ] Add games to the bot
- [ ] Add multiple languages to the bot
- [x] Create a requirements.txt file
- [ ] Improve SQL so it can add missing columns
- [ ] Add economy system
- [ ] Add more server specific settings
- [ ] Remove spagetti-code
- [ ] Improve security and stability of the [BetterMusicControl](https://github.com/staubtornado/BetterMusicControl/releases)-Integration
- [ ] Add dislikes back

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