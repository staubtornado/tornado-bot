from asyncio import sleep
from copy import copy
from math import ceil
from traceback import format_exc

from discord import ApplicationContext, Embed, Bot, slash_command, VoiceChannel, ClientException, Member, Option, \
    AutocompleteContext
from discord.ext.commands import Cog, check
from discord.utils import get, basic_autocomplete
from psutil import virtual_memory
from spotipy import SpotifyException
from yt_dlp import utils

from cogs.settings import Settings
from data.config.settings import SETTINGS
from data.db.memory import database
from lib.music.exceptions import YTDLError
from lib.music.extraction import YTDLSource
from lib.music.song import Song, SongStr
from lib.music.spotify import SpotifyScraping
from lib.music.voicestate import VoiceState
from lib.utils.utils import ordinal, save_traceback

utils.bug_reports_message = lambda: ''


class CustomApplicationContext(ApplicationContext):
    voice_state: VoiceState


async def auto_complete(ctx: AutocompleteContext) -> list:
    return ["Charts", "New Releases", "TDTT", "ESC22", "Chill", "Party", "Classical", "K-Pop", "Gaming", "Rock"]


def ensure_voice_state(ctx: CustomApplicationContext, requires_song: bool = False, requires_queue: bool = False,
                       no_processing: bool = False):
    if ctx.author.voice is None:
        return "❌ **You are not** connected to a **voice** channel."

    if ctx.voice_client:
        if ctx.voice_client.channel != ctx.author.voice.channel:
            return f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}."

    if not ctx.voice_state.is_playing and requires_song:
        return "❌ **Nothing** is currently **playing**."
    if isinstance(ctx.voice_state.current, SongStr) and (requires_song or no_processing):
        return "❌ Next **song is** currently **processing**, please **wait**."

    if len(ctx.voice_state.songs) == 0 and requires_queue:
        return "❌ The **queue** is **empty**."

    if ctx.voice_state.processing and no_processing:
        return "⚠ I am **currently processing** the previous **request**."


class Music(Cog):
    """
    Play music from various sources like Spotify, YouTube or SoundCloud.
    YouTube and Spotify playlists are supported, too.
    """
    def __init__(self, bot: Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: ApplicationContext) -> VoiceState:
        state = self.voice_states.get(ctx.guild_id)
        if not state or not state.exists:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild_id] = state
        return state

    def cog_unload(self):
        self.check_activity.stop()
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx: ApplicationContext):
        cur = database.cursor()

        cur.execute("""INSERT OR IGNORE INTO settings (GuildID) VALUES (?)""", (ctx.guild.id,))
        cur.execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", (ctx.guild.id, ))
        ctx.voice_state = self.get_voice_state(ctx)

    @slash_command()
    async def join(self, ctx: CustomApplicationContext):
        """Joins a voice channel."""

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        destination: VoiceChannel = ctx.author.voice.channel
        try:
            ctx.voice_state.voice = await destination.connect()
        except ClientException:
            guild_channel = get(self.bot.voice_clients, guild=ctx.guild)
            if guild_channel == destination:
                pass
            else:
                await guild_channel.disconnect(force=True)
                ctx.voice_state.voice = await destination.connect()
        await ctx.guild.change_voice_state(channel=destination, self_mute=False, self_deaf=True)
        await ctx.respond(f"👍 **Hello**! Joined {ctx.author.voice.channel.mention}.")

    @slash_command()
    async def clear(self, ctx: CustomApplicationContext):
        """Clears the whole queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.songs.clear()
        ctx.voice_state.loop = False
        await ctx.respond("🧹 **Cleared** the queue.")

    @slash_command()  # TODO: MERGE WITH JOIN COMMAND
    async def summon(self, ctx: CustomApplicationContext, *, channel: VoiceChannel = None):
        """Summons the bot to a voice channel. If no channel was specified, it joins your channel."""

        if not channel and not ctx.author.voice:
            await ctx.respond("❌ You are **not in a voice channel** and you **did not specify** a voice "
                              "channel.")
            return

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            await ctx.guild.change_voice_state(channel=destination, self_mute=False, self_deaf=True)
            await ctx.respond(f"👍 **Hello**! Joined {destination.mention}.")
            return

        ctx.voice_state.voice = await destination.connect()
        await ctx.guild.change_voice_state(channel=destination, self_mute=False, self_deaf=True)
        await ctx.respond(f"👍 **Hello**! Joined {destination.mention}.")

    @slash_command()
    async def leave(self, ctx: CustomApplicationContext):
        """Clears the queue and leaves the voice channel."""
        try:
            await ctx.voice_state.stop()
            voice_channel = get(self.bot.voice_clients, guild=ctx.guild)
            if voice_channel:
                await voice_channel.disconnect(force=True)

            await ctx.respond(f"👋 **Bye**. Left {ctx.author.voice.channel.mention}.")
        except AttributeError:
            await ctx.respond(f"⚙ I am **not connected** to a voice channel so my **voice state has been reset**.")
        del self.voice_states[ctx.guild.id]

    @slash_command()
    async def volume(self, ctx: CustomApplicationContext, volume: int):
        """Sets the volume of the current song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_song=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if not (0 < volume <= 100):
            if volume > 100:
                await ctx.respond("The **volume** cannot be **larger than 100%**.")
            elif volume <= 0:
                await ctx.respond("The **volume cannot be turned off**. Use **/**`pause` pause.")
            return

        if volume < 50:
            emoji: str = "🔈"
        elif volume == 50:
            emoji: str = "🔉"
        else:
            emoji: str = "🔊"

        ctx.voice_state.current.source.volume = volume / 100
        await ctx.respond(f"{emoji} **Volume** of the song **set to {volume}%**.")

    @slash_command()
    async def now(self, ctx: CustomApplicationContext):
        """Displays the currently playing song."""
        await ctx.defer()

        try:
            await ctx.respond(embed=ctx.voice_state.current.create_embed(ctx.voice_state.songs,
                                                                         ctx.voice_state.embed_size))
        except AttributeError:
            await ctx.respond("❌ **Nothing** is currently **playing**.")

    @slash_command()
    async def pause(self, ctx: CustomApplicationContext):
        """Pauses the currently playing song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_song=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.respond("⏯ **Paused** song, use **/**`resume` to **continue**.")

            for i in range(10):
                await sleep(SETTINGS["Cogs"]["Music"]["MaxDuration"] / 10)
                try:
                    if ctx.voice_state.voice.is_paused():
                        if i >= 9:
                            ctx.voice_state.loop = False
                            ctx.voice_state.songs.clear()
                            ctx.voice_state.voice.stop()
                            ctx.voice_state.current = None
                            await ctx.send("💤 **Stopped** the player **due to inactivity**.")
                            break
                    else:
                        break
                except AttributeError:
                    break
            return
        await ctx.respond("❌ The **song** is **already paused**.")

    @slash_command()
    async def resume(self, ctx: CustomApplicationContext):
        """Resumes a currently paused song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            return await ctx.respond("⏯ **Resumed** song, use **/**`pause` to **pause**.")
        await ctx.respond("❌ Either is the **song is not paused**, **or nothing** is currently **playing**.")

    @slash_command()
    async def stop(self, ctx: CustomApplicationContext):
        """Stops playing song and clears the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.loop = False
        ctx.voice_state.songs.clear()
        ctx.voice_state.voice.stop()
        ctx.voice_state.current = None
        await ctx.respond("⏹ **Stopped** the player and **cleared** the **queue**.")
        return

    @slash_command()
    async def skip(self, ctx: CustomApplicationContext,
                   force: Option(str, "Bypasses votes and directly skips song.", choices=["True"],
                                 required=False) = "False"):
        """Vote to skip a song. The requester can automatically skip."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_song=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        songs_to_skip: list = []
        loop_note: str = "."
        if ctx.voice_state.iterate:
            loop_note: str = " and **removed song from** queue **loop**."

            for i, song in enumerate(ctx.voice_state.songs):
                if isinstance(song, Song):
                    if song.source.url == ctx.voice_state.current.source.url:
                        songs_to_skip.append(i)

        voter: Member = ctx.author

        if force == "True":
            for role in voter.roles:
                if "DJ" in role.name:
                    ctx.voice_state.skip()
                    for i in songs_to_skip:
                        ctx.voice_state.songs.remove(i)

                    await ctx.respond(f"⏭ **Forced to skip** current song{loop_note}")
                    return
            for role in ctx.guild.roles:
                if "DJ" in role.name:
                    await ctx.respond(f"❌ You are **not a DJ**.")
                    return
            await ctx.respond(f"❌ **Only a DJ can force** song **skipping**.\nRoles that have `DJ` in their name are "
                              f"valid.")
            return

        if voter == ctx.voice_state.current.requester:
            await ctx.respond(f"⏭ **Skipped** the **song directly**, cause **you** added it{loop_note}")
            ctx.voice_state.skip()
            for i in songs_to_skip:
                ctx.voice_state.songs.remove(i)

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            required_votes: int = ceil(len([member for member in ctx.author.voice.channel.members if not member.bot])
                                       * (1 / 3))

            if total_votes >= required_votes:
                await ctx.respond(f"⏭ **Skipped song**, as **{total_votes}/{required_votes}** users voted{loop_note}")
                ctx.voice_state.skip()
                for i in songs_to_skip:
                    ctx.voice_state.songs.remove(i)
            else:
                await ctx.respond(f"🗳️ **Skip vote** added: **{total_votes}/{required_votes}**")
        else:
            await ctx.respond("❌ **Cheating** not allowed**!** You **already voted**.")

    @slash_command()
    async def queue(self, ctx: CustomApplicationContext, *, page: int = 1):
        """Shows the queue. You can optionally specify the page to show. Each page contains 10 elements."""
        await ctx.defer()

        if len(ctx.voice_state.songs) == 0:
            await ctx.respond('❌ The **queue** is **empty**.')
            return

        items_per_page = 10
        pages = ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue: str = ""
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            if isinstance(song, Song):
                queue += f"`{i + 1}`. [{song.source.title_limited_embed}]({song.source.url})\n"
            else:
                queue += f"`{i + 1}`. {song}\n"

        embed: Embed = Embed(title="Queue",
                             description=f"**Songs:** {len(ctx.voice_state.songs)}\n**Duration:** "
                                         f"{YTDLSource.parse_duration(ctx.voice_state.songs.get_duration())}\n⠀",
                             colour=0xFF0000)
        embed.add_field(name="🎶 Now Playing", value=f"[{ctx.voice_state.current.source.title_limited_embed}]"
                                                    f"({ctx.voice_state.current.source.url})\n"
                                                    f"[{ctx.voice_state.current.source.uploader}]"
                                                    f"({ctx.voice_state.current.source.uploader_url})", inline=False)
        embed.add_field(name="⠀", value=queue, inline=False)
        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.respond(embed=embed)

    @slash_command()
    async def shuffle(self, ctx: CustomApplicationContext):
        """Shuffles the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.songs.shuffle()
        await ctx.respond("🔀 **Shuffled** the queue.")

    @slash_command()
    async def reverse(self, ctx: CustomApplicationContext):
        """Reverses the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.songs.reverse()
        await ctx.respond("↩ **Reversed** the **queue**.")

    @slash_command()
    async def remove(self, ctx: CustomApplicationContext, index: int):
        """Removes a song from the queue at a given index."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        try:
            if index < 0:
                raise IndexError
            ctx.voice_state.songs.remove(index - 1)
        except IndexError:
            await ctx.respond(f"❌ There is **no song with** the **{ordinal(n=index)} position** in queue.")
            return
        await ctx.respond(f"🗑 **Removed** the **{ordinal(n=index)} song** in queue.")

    @slash_command()
    async def loop(self, ctx: CustomApplicationContext):
        """Loops the currently playing song. Invoke this command again to disable loop."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_song=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.loop = not ctx.voice_state.loop

        if ctx.voice_state.loop:
            await ctx.respond("🔁 **Looped song /**`loop` to **disable** loop.\n"
                              "❔ Looking for **queue loop?** **/**`iterate`")
            return
        await ctx.respond("🔁 **Unlooped song /**`loop` to **enable** loop.")

    @slash_command()
    async def iterate(self, ctx: CustomApplicationContext):
        """Iterates the current queue. Invoke this command again to disable iteration."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if ctx.voice_state.songs.get_duration() > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
            await ctx.respond("❌ The **queue is too long** to be iterated through.")
            return

        ctx.voice_state.iterate = not ctx.voice_state.iterate
        if ctx.voice_state.iterate:
            await ctx.voice_state.songs.put(copy(ctx.voice_state.current))

            await ctx.respond(f"🔁 **Looped queue /**`iterate` to **disable** loop.")
            return
        await ctx.respond(f"🔁 **Unlooped queue /**`iterate`e to **enable** loop.")

    @slash_command()
    @check(Settings.has_beta)
    async def play(self, ctx: CustomApplicationContext,
                   search: Option(str, "Enter the name of the song, a URL or a preset.",
                                  autocomplete=basic_autocomplete(auto_complete), required=True)):
        """Play a song through the bot, by searching a song with the name or by URL."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if len(ctx.voice_state.songs) >= SETTINGS["Cogs"]["Music"]["MaxQueueLength"]:
            await ctx.respond("🥵 **Too many** songs in queue.")
            return

        if virtual_memory().percent > 75 and SETTINGS["Production"]:
            await ctx.respond("🔥 **I am** currently **experiencing high usage**. Please **try again later**.")
            return

        if not ctx.voice_state.voice:
            await self.join(ctx)

        async def add_song(track_name: str, fetch_source: bool = False):
            if not fetch_source:
                await ctx.voice_state.songs.put(SongStr(track_name, ctx))
                return

            try:
                source = await YTDLSource.create_source(ctx, track_name.replace(":", ""), loop=self.bot.loop)
            except Exception as error:
                return error

            if not ctx.voice_state.voice:
                await self.join(ctx)

            song = Song(source)
            await ctx.voice_state.songs.put(song)
            return source

        presets: dict = {"Charts": "https://open.spotify.com/playlist/37i9dQZEVXbNG2KDcFcKOF",
                         "New Releases": "https://open.spotify.com/playlist/37i9dQZF1DWUW2bvSkjcJ6",
                         "Chill": "https://open.spotify.com/playlist/37i9dQZF1DWTvNyxOwkztu",
                         "Party": "https://open.spotify.com/playlist/37i9dQZF1DXbX3zSzB4MO0",
                         "Classical": "https://open.spotify.com/playlist/37i9dQZF1DWWEJlAGA9gs0",
                         "K-Pop": "https://open.spotify.com/playlist/37i9dQZF1DX9tPFwDMOaN1",
                         "Gaming": "https://open.spotify.com/playlist/37i9dQZF1DWTyiBJ6yEqeu",
                         "Rock": "https://open.spotify.com/playlist/37i9dQZF1DWZJhOVGWqUKF",
                         "TDTT": "https://open.spotify.com/playlist/669nUqEjX1ozcx2Uika2fR",
                         "ESC22": "https://open.spotify.com/playlist/37i9dQZF1DWVCKO3xAlT1Q"}

        search: str = presets[search] if search in presets else search

        async def process():
            if any(x in search for x in ["https://open.spotify.com/playlist/", "spotify:playlist:",
                                         "https://open.spotify.com/album/", "spotify:album:",
                                         "https://open.spotify.com/track/", "spotify:track:",
                                         "https://open.spotify.com/artist/", "spotify:artist:"]):
                song_names: list = []

                try:
                    if "playlist" in search:
                        song_names.extend(SpotifyScraping.get_playlist_track_names(search))
                    elif "album" in search:
                        song_names.extend(SpotifyScraping.get_album_track_names(search))
                    elif "track" in search:
                        song_names.append(SpotifyScraping.get_track_name(search))
                    elif "artist" in search:
                        song_names.extend(SpotifyScraping.get_artist_top_songs(search))
                    else:
                        raise SpotifyException

                except SpotifyException:
                    await ctx.respond("❌ **Invalid** or **unsupported** Spotify **link**.")
                    return

                for i, song_name in enumerate(song_names):
                    if not len(ctx.voice_state.songs) >= 100:
                        await add_song(song_name)
                        continue
                    await ctx.respond(f"❌ **Queue reached its limit in size**, therefore **only {i + 1} songs added** "
                                      f"from **Spotify**.")
                    return

                info: str = song_names[0].replace(" by ", "** by **") if len(song_names) == 1 else \
                    f"{len(song_names)} songs"
                await ctx.respond(f"✅ Added **{info}** from **Spotify**.")
                return

            video_type = await YTDLSource.check_type(search, loop=self.bot.loop)
            if video_type in ["playlist", "playlist_alt"]:
                videos = await YTDLSource.create_source_playlist(video_type, search, loop=self.bot.loop)
                for i, url in enumerate(videos):
                    if not len(ctx.voice_state.songs) >= 100:
                        await add_song(url)
                        continue
                    await ctx.respond(f"❌ **Queue reached its limit in size**, therefore **only {i + 1} songs added** "
                                      f"from **Youtube**.")
                    return
                await ctx.respond(f"✅ Added **{len(videos)}** from **YouTube**.")
                return

            name = await add_song(search, fetch_source=True)
            if isinstance(name, YTDLError):
                await ctx.respond(f"❌ {name}")
            elif isinstance(name, utils.GeoRestrictedError):
                await ctx.respond("🌍 This **video** is **not available in** my **country**.")
            elif isinstance(name, utils.UnavailableVideoError):
                await ctx.respond("🚫 This **video is **not available**.")
            elif isinstance(name, Exception):
                traceback = format_exc()
                print(traceback) if traceback is not None else None
                await ctx.respond(f"❌ **Error**: `{name}`")
            else:
                await ctx.respond(f'✅ Added {name}')

        ctx.voice_state.processing = True
        try:
            await process()
        except Exception as e:
            save_traceback(e)
            await ctx.respond(f"❌ **A fatal error has occurred**: `{e}`. **You might** execute **/**`leave` to **reset "
                              f"the voice state on** this **server**.")
        ctx.voice_state.processing = False

    @slash_command()
    async def supported_links(self, ctx: CustomApplicationContext):
        """Lists all supported music streaming services."""
        await ctx.respond(embed=Embed(title="Supported Links", description="All supported streaming services.",
                                      colour=0xFF0000)
                          .add_field(name="YouTube", value="✅ Tracks\n❌ Playlists\n❌ Albums\n❌ Artists\n⚠ Livestreams")
                          .add_field(name="YouTube Music", value="✅ Tracks\n❌ Playlists\n❌ Albums\n❌ Artists")
                          .add_field(name="Spotify", value="✅ Tracks\n✅ Playlists\n✅ Albums\n✅ Artists")
                          .add_field(name="Soundcloud", value="✅ Tracks\n❌ Playlists\n❌ Albums\n❌ Artists")
                          .add_field(name="Twitch", value="⚠ Livestreams")
                          .add_field(name="🐞 Troubleshooting", value="If you are experiencing issues, please execute"
                                                                     " **/**`leave`. This should fix most errors.",
                                     inline=False))


def setup(bot):
    bot.add_cog(Music(bot))
