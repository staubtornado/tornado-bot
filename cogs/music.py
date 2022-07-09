from asyncio import sleep
from math import ceil
from time import time
from typing import Union, Optional

from discord import ApplicationContext, Embed, Bot, slash_command, VoiceChannel, ClientException, Member, Option, \
    AutocompleteContext, HTTPException, VoiceProtocol, VoiceClient, StageChannel
from discord.ext.commands import Cog, check
from discord.utils import get, basic_autocomplete
from psutil import virtual_memory
from spotipy import SpotifyException
from yt_dlp import utils

from cogs.settings import Settings
from data.config.settings import SETTINGS
from data.db.memory import database
from lib.music.api import search_on_spotify, get_lyrics
from lib.music.exceptions import YTDLError
from lib.music.extraction import YTDLSource
from lib.music.search import process
from lib.music.song import Song, SongStr
from lib.music.voicestate import VoiceState
from lib.utils.utils import ordinal, progress_bar, time_to_string

utils.bug_reports_message = lambda: ''


class CustomApplicationContext(ApplicationContext):
    voice_state: VoiceState
    priority: bool = False


async def auto_complete(ctx: AutocompleteContext) -> list[str]:
    rtrn = ["Charts", "New Releases", "TDTT", "ESC22", "Chill", "Party", "Classical", "K-Pop", "Gaming", "Rock"]

    if len([x for x in rtrn if x.lower().startswith(ctx.value.lower())]) > 0:
        return [x for x in rtrn if x.lower().startswith(ctx.value.lower())]

    rtrn.clear()
    try:
        response = search_on_spotify(search=ctx.value)
        for item in response[0] + response[1]:
            rtrn.append(item) if item not in rtrn else None
    except SpotifyException:
        pass
    return rtrn if len(rtrn) > 0 else ["Charts", "New Releases", "TDTT", "ESC22", "Chill", "Party", "Classical",
                                       "K-Pop", "Gaming", "Rock"]


def ensure_voice_state(ctx: CustomApplicationContext, **kwargs) -> Union[str, None]:
    if ctx.author.voice is None and not kwargs.get("no_voice_required"):
        return "❌ **You are not** connected to a **voice** channel."

    if ctx.voice_client:
        if ctx.voice_client.channel != ctx.author.voice.channel:
            return f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}."

    if not ctx.voice_state.is_playing and kwargs.get("requires_song"):
        return "❌ **Nothing** is currently **playing**."
    if isinstance(ctx.voice_state.current, SongStr) and (kwargs.get("requires_song") or kwargs.get("no_processing")):
        return "❌ Next **song is** currently **processing**, please **wait**."

    if not len(ctx.voice_state.songs) + len(ctx.voice_state.priority_songs) and kwargs.get("requires_queue"):
        return "❌ The **queue** is **empty**."

    if ctx.voice_state.processing and kwargs.get("no_processing"):
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
        state: VoiceState = self.voice_states.get(ctx.guild_id)
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
        cur.execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", (ctx.guild.id,))
        ctx.voice_state = self.get_voice_state(ctx)
        ctx.priority = False

    @slash_command()
    async def join(self, ctx: CustomApplicationContext, channel: Optional[VoiceChannel]):
        """Joins a voice channel."""

        instance: Union[str, None] = ensure_voice_state(ctx, no_voice_required=bool(channel))
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        destination: Union[VoiceChannel, StageChannel] = channel or ctx.author.voice.channel
        if ctx.guild.voice_client:
            await ctx.respond(f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}.")
            return

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
        await ctx.respond(f"👍 **Hello**! Joined {destination.mention}.")

    @slash_command()
    async def clear(self, ctx: CustomApplicationContext):
        """Clears the whole queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.songs.clear()
        ctx.voice_state.priority_songs.clear()
        ctx.voice_state.loop = False
        await ctx.respond("🧹 **Cleared** the queue.")

    @slash_command()
    async def leave(self, ctx: CustomApplicationContext):
        """Clears the queue and leaves the voice channel."""

        voice: Union[VoiceProtocol, VoiceClient, None] = ctx.voice_state.voice

        if not isinstance(voice, VoiceClient):
            voice = get(self.bot.voice_clients, guild=ctx.guild)
        await ctx.voice_state.stop()

        if isinstance(voice, VoiceProtocol):
            await voice.disconnect(force=True)
        del self.voice_states[ctx.guild.id]

        try:
            await ctx.respond(f"👋 **Bye**. Left {voice.channel.mention}.")
        except AttributeError:
            await ctx.respond(f"⚙ I am **not connected** to a voice channel so my **voice state has been reset**.")

    @slash_command()
    async def volume(self, ctx: CustomApplicationContext, volume: int):
        """Changes the volume of the current song."""
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

        ctx.voice_state.current.source.volume = volume / 100
        emoji: str = "🔈" if volume < 50 else "🔉" if volume == 50 else "🔊"
        await ctx.respond(f"{emoji} **Volume** of the song **set to {volume}%**.")

    @slash_command()
    async def now(self, ctx: CustomApplicationContext):
        """Currently playing song."""
        await ctx.defer()

        try:
            songs: tuple = (ctx.voice_state.songs, ctx.voice_state.priority_songs)
            embed: Embed = ctx.voice_state.current.create_embed(songs, ctx.voice_state.embed_size)
        except AttributeError:
            await ctx.respond("❌ **Nothing** is currently **playing**.")
            return

        duration: int = int(ctx.voice_state.current.source.data.get('duration'))
        if not ctx.voice_state.voice.is_paused():
            if not ctx.voice_state.song_position[0] + (round(time()) - ctx.voice_state.song_position[1]) > duration:
                ctx.voice_state.song_position[0] += round(time()) - ctx.voice_state.song_position[1]
            else:
                ctx.voice_state.song_position[0] = duration
            ctx.voice_state.song_position[1] = round(time())

        bar = progress_bar(ctx.voice_state.song_position[0], duration, content=("---", "•**", "---"))
        embed.description = f"**{time_to_string(ctx.voice_state.song_position[0])} {bar} " \
                            f"**{time_to_string(duration)}**\n" \
                            f"{embed.description}".replace(f"**|** {ctx.voice_state.current.source.duration} ", "")
        await ctx.respond(embed=embed)

    @slash_command()
    async def pause(self, ctx: CustomApplicationContext):
        """Pauses the current song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_song=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            ctx.voice_state.song_position[0] += round(time()) - ctx.voice_state.song_position[1]
            ctx.voice_state.song_position[1] = round(time())
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
        """Resumes the paused song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            ctx.voice_state.song_position[1] = round(time())
            return await ctx.respond("⏯ **Resumed** song, use **/**`pause` to **pause**.")
        await ctx.respond("❌ Either is the **song is not paused**, **or nothing** is currently **playing**.")

    @slash_command()
    async def stop(self, ctx: CustomApplicationContext):
        """Stops playing and clears the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.loop = False
        ctx.voice_state.songs.clear()
        ctx.voice_state.priority_songs.clear()
        ctx.voice_state.voice.stop()
        ctx.voice_state.current = None
        await ctx.respond("⏹ **Stopped** the player and **cleared** the **queue**.")
        return

    @slash_command()
    async def skip(self, ctx: CustomApplicationContext,
                   force: Option(str, "Bypasses votes and directly skips song.", choices=["True"],
                                 required=False) = "False"):
        """(Vote) skip to the next song. The requester can always skip."""
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
            required: int = ceil(len([member for member in ctx.author.voice.channel.members if not member.bot]) / 3)

            if total_votes >= required:
                await ctx.respond(f"⏭ **Skipped song**, as **{total_votes}/{required}** users voted{loop_note}")
                ctx.voice_state.skip()
                for i in songs_to_skip:
                    ctx.voice_state.songs.remove(i)
            else:
                await ctx.respond(f"🗳️ **Skip vote** added: **{total_votes}/{required}**")
        else:
            await ctx.respond("❌ **Cheating** not allowed**!** You **already voted**.")

    @slash_command()
    async def history(self, ctx: CustomApplicationContext):
        """Latest played songs in the current session."""
        await ctx.defer()

        if not len(ctx.voice_state.history):
            await ctx.respond("There is **no data in** this **session**.")
            return

        embed: Embed = Embed(title="History", description="Latest played songs in this session.\n\n", colour=0xFF0000)
        for i, item in enumerate(ctx.voice_state.history, start=1):
            embed.description += f"`{i}`. {item}\n"
        await ctx.respond(embed=embed)

    @slash_command()
    async def queue(self, ctx: CustomApplicationContext, page: int = 1):
        """Shows the queue. You can optionally specify the page to show."""
        await ctx.defer()

        if not len(ctx.voice_state.songs) + len(ctx.voice_state.priority_songs):
            await ctx.respond('❌ The **queue** is **empty**.')
            return

        items_per_page = 10
        pages = ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue: str = ""
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            if isinstance(song, Song):
                queue += f"`{i + 1 + len(ctx.voice_state.priority_songs)}`. [{song.source.title_limited_embed}]" \
                         f"({song.source.url})\n"
            else:
                queue += f"`{i + 1 + len(ctx.voice_state.priority_songs)}`. {song}\n"

        embed: Embed = Embed(title="Queue",
                             description=f"**Songs:** "
                                         f"{len(ctx.voice_state.songs) + len(ctx.voice_state.priority_songs)}"
                                         f"\n**Duration:** "
                                         f"{YTDLSource.parse_duration(ctx.voice_state.songs.get_duration())}\n⠀",
                             colour=0xFF0000)
        embed.add_field(name="🎶 Now Playing", value=f"[{ctx.voice_state.current.source.title_limited_embed}]"
                                                    f"({ctx.voice_state.current.source.url})\n"
                                                    f"[{ctx.voice_state.current.source.uploader}]"
                                                    f"({ctx.voice_state.current.source.uploader_url})", inline=False)
        p_queue: str = ""
        for i, song in enumerate(ctx.voice_state.priority_songs, start=1):
            if isinstance(song, Song):
                p_queue += f"`{i}.` [{song.source.title_limited_embed}]({song.source.url} " \
                           f"'{song.source.title}')\n"
            else:
                p_queue += f"`{i}.` {song}\n"
        embed.add_field(name="\nPriority Queue", value=p_queue, inline=False) if p_queue != "" else None

        embed.add_field(name="⠀\nQueue", value=queue, inline=False) if queue != "" else None
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
        ctx.voice_state.priority_songs.shuffle() if len(ctx.voice_state.priority_songs) > 0 else None
        await ctx.respond("🔀 **Shuffled** the queue.")

    @slash_command()
    async def reverse(self, ctx: CustomApplicationContext):
        """Reverses the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        ctx.voice_state.songs.reverse() if len(ctx.voice_state.songs) else None
        ctx.voice_state.priority_songs.reverse() if len(ctx.voice_state.priority_songs) else None
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
            if index <= len(ctx.voice_state.priority_songs):
                ctx.voice_state.priority_songs.remove(index - 1)
            else:
                ctx.voice_state.songs.remove(index - 1 - len(ctx.voice_state.priority_songs))
        except IndexError:
            await ctx.respond(f"❌ There is **no song with** the **{ordinal(n=index)} position** in queue.")
            return
        await ctx.respond(f"🗑 **Removed** the **{ordinal(n=index)} song** in queue.")

    @slash_command()
    async def loop(self, ctx: CustomApplicationContext):
        """Loops current song. Invoke this command again to disable loop."""
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
        """Iterates current queue. Invoke this command again to disable iteration."""
        await ctx.defer()

        instance = ensure_voice_state(ctx, requires_queue=True, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if ctx.voice_state.songs.get_duration() > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
            await ctx.respond("❌ The **queue is too long** to be iterated through.")
            return

        ctx.voice_state.iterate = not ctx.voice_state.iterate
        if ctx.voice_state.iterate:
            await ctx.voice_state.songs.put(SongStr(ctx.voice_state.current, ctx))

            await ctx.respond(f"🔁 **Looped queue**, use **/**`iterate` to **disable** loop.")
            return
        await ctx.respond(f"🔁 **Unlooped queue**, use **/**`iterate` to **enable** loop.")

    @slash_command()
    async def lyrics(self, ctx: CustomApplicationContext, title: str = None, artist: str = None):
        """Search for lyrics, default search is current song."""
        await ctx.defer()

        try:
            response = get_lyrics(title or ctx.voice_state.current.source.title,
                                  artist or ctx.voice_state.current.source.uploader)

            embed = Embed(title="Lyrics", description=response[0], colour=0xFF0000)
            embed.set_author(name=f"{response[2]} by {response[3]}", icon_url=response[1])
            await ctx.respond(embed=embed)
        except (AttributeError, HTTPException):
            await ctx.respond("❌ **Can not find any lyrics** for that song.")

    @slash_command()
    @check(Settings.has_beta)
    async def next(self, ctx: CustomApplicationContext,
                   search: Option(str, "Enter the name of the song, a url or a preset.",
                                  autocomplete=basic_autocomplete(auto_complete), required=True)):
        """Adds a song to the priority queue."""
        ctx.priority = bool(len(ctx.voice_state.songs))
        await self.play(ctx, search)

    @slash_command()
    @check(Settings.has_beta)
    async def play(self, ctx: CustomApplicationContext,
                   search: Option(str, "Enter the name of the song, a URL or a preset.",
                                  autocomplete=basic_autocomplete(auto_complete), required=True)):
        """Play a song through the bot. Enter link (song or Playlist) or song name"""
        await ctx.defer()

        instance = ensure_voice_state(ctx, no_processing=True)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if len(ctx.voice_state.songs) >= SETTINGS["Cogs"]["Music"]["MaxQueueLength"]:
            await ctx.respond("🥵 **Too many songs** in queue.")
            return

        if virtual_memory().percent > 75 and SETTINGS["Production"]:
            await ctx.respond("🔥 **I am** currently **experiencing high usage**. Please **try again later**.")
            return

        try:
            if not ctx.guild.voice_client:
                raise ClientException
        except ClientException:
            await self.join(ctx, None)

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
        search: str = presets.get(search) or search

        ctx.voice_state.processing = True
        try:
            source = await process(search, ctx, self.bot.loop, ctx.priority)
        except YTDLError as e:
            source = e
        except Exception as e:
            ctx.voice_state.processing = False
            raise e
        ctx.voice_state.processing = False

        if isinstance(source, str) or isinstance(source, YTDLError):
            await ctx.respond(source)
            return
        await ctx.respond(f"✅ Added {source} {'to **priority queue**' if ctx.priority else ''}")


def setup(bot):
    bot.add_cog(Music(bot))
