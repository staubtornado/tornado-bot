from asyncio import TimeoutError
from http.client import HTTPException
from math import ceil
from random import randint, shuffle
from typing import Optional, Union

from asyncspotify import FullTrack, SimpleTrack
from discord import Bot, ApplicationContext, slash_command, VoiceChannel, StageChannel, ClientException, \
    VoiceProtocol, Option, AutocompleteContext, Embed, ButtonStyle, Interaction, WebhookMessage, Forbidden, Member, \
    VoiceClient
from discord.ext.commands import Cog
from discord.utils import basic_autocomplete
from psutil import virtual_memory
from spotipy import SpotifyException

from bot import CustomBot
from data.config.settings import SETTINGS
from lib.db.data_objects import EmbedSize
from lib.music.api import search_on_spotify, get_lyrics
from lib.music.betterMusicControl import BetterMusicControlReceiver
from lib.music.exceptions import YTDLError
from lib.music.music_application_context import MusicApplicationContext
from lib.music.other import ensure_voice_state
from lib.music.prepared_source import PreparedSource
from lib.music.presets import PRESETS
from lib.music.process import process, AdditionalInputRequiredError
from lib.music.song import Song
from lib.music.views import LoopDecision, PlaylistParts, VariableButton
from lib.music.voicestate import VoiceState, Loop
from lib.utils.utils import ordinal, time_to_string, progress_bar


async def auto_complete(ctx: AutocompleteContext) -> list[str]:
    rtrn = list(PRESETS.keys())

    if len([x for x in rtrn if x.lower().startswith(ctx.value.lower())]) > 0:
        return [x for x in rtrn if x.lower().startswith(ctx.value.lower())]

    rtrn.clear()
    try:
        response = search_on_spotify(search=ctx.value)
        for item in response[0] + response[1]:
            rtrn.append(item) if item not in rtrn else None
    except SpotifyException:
        pass
    return rtrn if len(rtrn) > 0 else list(PRESETS.keys())


class Music(Cog):
    """
    Play music from various sources like Spotify, YouTube or SoundCloud.
    YouTube and Spotify playlists are supported, too.
    """

    bot: CustomBot
    voice_states: dict[int, VoiceState]
    _bmc: BetterMusicControlReceiver

    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self.voice_states = {}
        self._bmc = BetterMusicControlReceiver(bot)

    async def get_voice_state(self, ctx: ApplicationContext) -> VoiceState:
        state: Optional[VoiceState] = self.voice_states.get(ctx.guild_id)
        if not state or not state.is_valid:
            state = await VoiceState.create(self.bot, ctx)
            self.voice_states[ctx.guild_id] = state
        return state

    def cog_unload(self) -> None:
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx: ApplicationContext) -> None:
        ctx.voice_state = await self.get_voice_state(ctx)
        ctx.playnext = False

    @Cog.listener()  # Needed to prevent song hang-ups when bot changes voice.
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if not member.id == self.bot.user.id or before.channel == after.channel:
            return
        restart: bool = False
        voice_state: VoiceState = self.voice_states.get(member.guild.id)

        if before.channel is None and after.channel is not None:
            if self.voice_states.get(after.channel.guild.id).is_valid:
                restart = bool(voice_state.voice)
        elif before.channel is not None and after.channel is None:

            #  Wait several seconds and check if the disconnect was intentional.
            def check(m: Member, b: VoiceState, a: VoiceState) -> bool:
                return m.id == self.bot.user.id and b.channel is not None and a.channel is None
            try:
                await self.bot.wait_for("voice_state_update", check=check, timeout=3)
            except TimeoutError:
                if voice_state is not None and voice_state.is_valid:
                    await voice_state.stop()
            return
        elif before.channel is not None and after.channel is not None:
            if before.channel.id != after.channel.id:
                restart = True

        if restart:
            voice_state.voice.pause()
            voice_state.voice.resume()

    @slash_command()
    async def join(self, ctx: MusicApplicationContext, channel: Optional[VoiceChannel] = None) -> None:
        """Summons the bot into a voice channel."""

        try:
            ensure_voice_state(ctx, no_voice_required=bool(channel))
        except ValueError as e:
            await ctx.respond(str(e))
            return

        if ctx.voice_state.is_playing:
            await ctx.respond(f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}.")
            return
        destination: Union[VoiceChannel, StageChannel] = channel or ctx.author.voice.channel

        try:
            ctx.voice_state.voice = await destination.connect()
        except ClientException:
            await ctx.guild.voice_client.disconnect(force=True)
            ctx.voice_state.voice = await destination.connect()
        ctx.voice_state.skip()
        await ctx.guild.change_voice_state(channel=destination, self_mute=False, self_deaf=True)
        await ctx.respond(f"👍 **Hello**! Joined {destination.mention}.")

    @slash_command()
    async def stop(self, ctx: MusicApplicationContext) -> None:
        """Stops current song and clears the queue."""

        try:
            ensure_voice_state(ctx, no_processing=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        ctx.voice_state.loop = Loop.NONE
        ctx.voice_state.queue.clear()
        ctx.voice_state.voice.stop()
        ctx.voice_state.current = None
        ctx.voice_state.live = False
        await ctx.respond("⏹ **Stopped** song and **cleared** the **queue**.")

    @slash_command()
    async def leave(self, ctx: MusicApplicationContext) -> None:
        """Clears song queue and removes bot from voice channel."""

        if isinstance(ctx.guild.voice_client, VoiceProtocol):
            await ctx.respond(f"👋 **Bye**. Left {ctx.guild.voice_client.channel.mention}.")
            await ctx.guild.voice_client.disconnect(force=True)
        else:
            await ctx.respond("🔄 ️**Reset voice** state.")
        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild_id]

    @slash_command()
    async def play(self, ctx: MusicApplicationContext,
                   search: Option(str, "Name or URL of song, playlist URL, or preset.",
                                  autocomplete=basic_autocomplete(auto_complete), required=True)) -> None:
        """Play music in a voice channel."""
        await ctx.defer()

        try:
            ensure_voice_state(ctx, no_processing=True, no_live_notice=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        if virtual_memory().percent > 75 and SETTINGS["Production"]:
            await ctx.respond("🔥 **I am** currently **experiencing high usage**. Please **try again later**.")
            return

        if not ctx.guild.voice_client:
            await self.join(ctx, None)

        search = PRESETS.get(search) or search
        ctx.voice_state.processing = True
        try:
            song_s: Union[Song, list[Song]] = await process(search, ctx)
        except (ValueError, YTDLError) as e:
            await ctx.respond(str(e))
        except AdditionalInputRequiredError as e:
            view: PlaylistParts = PlaylistParts()
            for option in e.args[1]:
                view.add_item(VariableButton(
                    custom_id=str(randint(100000000, 999999999)),
                    callback=view.callback,
                    label=option,
                    style=ButtonStyle.green if "-" in option else ButtonStyle.blurple
                ))
            response: Union[Interaction, WebhookMessage] = await ctx.respond(e.args[0], view=view)
            await view.wait()

            tracks: list[Union[FullTrack, SimpleTrack, dict, Song]] = []
            match view.value:
                case None:
                    await response.edit(content="❌ **Timeout**. User did **not respond within given time**.", view=None)
                case "Help me choose.":
                    tracks.extend(e.args[2])
                    shuffle(tracks)
                case _:
                    answer: list[str] = str(view.value).split(" - ")
                    tracks = e.args[2][int(answer[0]) - 1:int(answer[1])]
            for track in tracks[:ctx.voice_state.queue.maxsize - len(ctx.voice_state.queue)]:
                ctx.voice_state.put(Song(PreparedSource(ctx, track)), ctx.playnext)
        else:
            if isinstance(song_s, list):
                if len(song_s) > 1:
                    await ctx.respond(f"✅ Enqueued **{len(song_s)} songs**.")
                    return
                song_s = song_s[0]

            if ctx.voice_state.is_playing or ctx.voice_state.voice.is_paused():
                if ctx.playnext:
                    await ctx.respond(f"🎶 **Playing** 🔎 `{str(song_s).replace(' by ', '` by `')}` **next**!")
                else:
                    await ctx.respond(f"✅ **Enqueued** 🔎 `{str(song_s).replace(' by ', '` by `')}`.")
            else:
                await ctx.respond(f"🎶 **Playing** 🔎 `{str(song_s).replace(' by ', '` by `')}` **now**!")
        finally:
            ctx.voice_state.processing = False

    @slash_command()
    async def playnext(self, ctx: MusicApplicationContext,
                       search: Option(str, "Name or URL of song, playlist URL, or preset.",
                                      autocomplete=basic_autocomplete(auto_complete), required=True)) -> None:
        """Same as /play but appends to front of queue."""
        ctx.playnext = True
        await self.play(ctx, search)

    @slash_command()
    async def queue(self, ctx: MusicApplicationContext, page: int = 1) -> None:
        """Shows the song queue."""

        size: int = len(ctx.voice_state.queue)
        if not size:
            await ctx.respond("❌ The **queue** is **empty**.")
            return

        start: int = (page - 1) * SETTINGS["Cogs"]["Music"]["Queue"]["ItemsPerPage"]
        end: int = start + SETTINGS["Cogs"]["Music"]["Queue"]["ItemsPerPage"]
        duration: int = ctx.voice_state.queue.duration

        description = (
            f"**Size**: `{size}`\n"
            f"**Duration**: `{time_to_string(duration)}`\n"
            f"\n"
            f"**Now Playing**\n"
            f"[{ctx.voice_state.current}]({ctx.voice_state.current.source.url})\n"
            f"\n"
            f"**Requesters**\n"
        )

        emojis: list[str] = [
            "<:aubanana:939542863929307216>",
            "<:aublue:939543978892722247>",
            "<:aubrown:939543989760167956>",
            "<:aucoral:939543993816064100>",
            "<:aucyan:939543991081398292>",
            "<:aublack:939543985620406272>",
            "<:augreen:939543980100698123>",
            "<:aulime:939543992490676234>",
            "<:aumaroon:939542861182025828>",
            "<:auorange:939543983019933726>",
            "<:aupink:939543981115715595>",
            "<:aupurple:939543988229267507>",
            "<:aured:939543977215008778>",
            "<:aurose:939542862595498004>",
            "<:autan:939542866294894642>",
            "<:auwhite:939543986723508255>",
            "<:auyellow:939543984139816991>",
            "<:augray:939542865200152616>"
        ]
        shuffle(emojis)

        requesters: dict[str, int] = {}
        for i, song in enumerate(ctx.voice_state.queue[start:end], start=start + 1):
            if not requesters.get(song.requester.mention):
                requesters[song.requester.mention] = end - i - 1
        for requester in requesters:
            description += f"{emojis[requesters[requester]]} {requester}\n"
        description += "\n**Queue**\n"

        for i, song in enumerate(ctx.voice_state.queue[start:end], start=start + 1):
            url: str = song.source.url.split("%")[0]
            description += f"`{i}.` {emojis[requesters[song.requester.mention]]} [{song}]({url})\n"

        embed: Embed = Embed(title="Queue", color=0xFF0000, description=description)
        embed.set_footer(
            text=f"Page {page}/{ceil(len(ctx.voice_state.queue) / SETTINGS['Cogs']['Music']['Queue']['ItemsPerPage'])}"
        )
        await ctx.respond(embed=embed)

    @slash_command()
    async def shuffle(self, ctx: MusicApplicationContext) -> None:
        """Shuffles the song queue."""

        try:
            ensure_voice_state(ctx, requires_queue=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        ctx.voice_state.queue.shuffle()
        await ctx.respond("🔀 **Shuffled** the queue.")

    @slash_command()
    async def reverse(self, ctx: MusicApplicationContext) -> None:
        """Reverses the song queue."""

        try:
            ensure_voice_state(ctx, requires_queue=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        ctx.voice_state.queue.reverse()
        await ctx.respond("↩ **Reversed** the **queue**.")

    @slash_command()
    async def remove(self, ctx: MusicApplicationContext, index: int) -> None:
        """Removes a song from the queue at a given index."""

        try:
            ensure_voice_state(ctx, requires_queue=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        if index < 1:
            await ctx.respond("❌ **Invalid index**.")
            return

        try:
            ctx.voice_state.queue.remove(index - 1)
        except IndexError:
            await ctx.respond(f"❌ There is **no song with** the **{ordinal(n=index)} position** in queue.")
            return
        await ctx.respond(f"🗑 **Removed** the **{ordinal(n=index)} song** in queue.")

    @slash_command()
    async def clear(self, ctx: MusicApplicationContext) -> None:
        """Clears the song queue."""

        try:
            ensure_voice_state(ctx, requires_queue=True, no_processing=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        ctx.voice_state.queue.clear()
        await ctx.respond("📂 **Cleared** the **queue**.")

    @slash_command()
    async def loop(self, ctx: MusicApplicationContext) -> None:
        """Loops current song/queue. Invoke again to disable loop."""
        await ctx.respond("⚠️**What** do you want **to change?**", view=LoopDecision(ctx))

    @slash_command()
    async def skip(self, ctx: MusicApplicationContext,
                   force: Option(str, "Bypasses votes and directly skips song.", choices=["True"],
                                 required=False) = "False") -> None:
        """(Vote) skip to next song. Requester can always skip."""

        try:
            ensure_voice_state(ctx, requires_song=True, no_live_notice=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        author = ctx.author
        if force == "True":
            if tuple(filter(lambda role: "DJ" in role.name, ctx.author.roles)) or author.guild_permissions.manage_guild:
                ctx.voice_state.skip()
                await ctx.respond(f"⏭ **Forced to skip** current song.")
                return
            if tuple(filter(lambda role: "DJ" in role.name, ctx.guild.roles)):
                await ctx.respond(f"❌ You are **not a DJ**.")
                return
            await ctx.respond(f"❌ **Only a DJ can force** song **skipping**.\n"
                              f"❔Roles that have `DJ` in their name are valid.")
            return

        if author == ctx.voice_state.current.requester:
            ctx.voice_state.skip()
            await ctx.respond(f"⏭ **Skipped** the **song directly**, cause **you** added it.")
            return

        if author.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(author.id)

            votes: int = len(ctx.voice_state.skip_votes)
            majority: int = ceil(len([member for member in ctx.author.voice.channel.members if not member.bot]) / 3)

            if votes >= majority:
                ctx.voice_state.skip()
                await ctx.respond(f"⏭ **Skipped song**, as **{votes}/{majority}** users voted.")
                return
            await ctx.respond(f"🗳️ **Skip vote** added: **{votes}/{majority}**")
            return
        await ctx.respond("❌ **Cheating** not allowed**!** You **already voted**.")

    @slash_command()
    async def now(self, ctx: MusicApplicationContext) -> None:
        """Current playing song with elapsed time."""

        if ctx.voice_state.live:
            await ctx.respond(
                "❌ **Not available while playing** a **live** stream.\n"
                "❔Execute **/**`stop` to **switch to default song streaming**."
            )
            return

        if ctx.voice_state.current is None:
            await ctx.respond("❌ **Nothing** is currently **playing**.")
            return

        if isinstance(ctx.voice_state.current.source, PreparedSource):
            await ctx.respond("⚠️Next song is **currently processing**.")
            return

        embed: Embed = ctx.voice_state.current.create_embed(
            EmbedSize(ctx.voice_state.embed_size), queue=ctx.voice_state.queue, loop=ctx.voice_state.loop
        )

        duration: int = int(ctx.voice_state.current.source.duration)
        elapsed: int = int(ctx.voice_state.voice.timestamp / 1000 * 0.02) - ctx.voice_state.position
        bar: str = progress_bar(elapsed, duration, content=("-", "•**", "-"), length=30)
        value: str = f"**{time_to_string(int(elapsed))} {bar} **{time_to_string(duration)}**"
        embed.insert_field_at(3, name="‎", value=value, inline=False)
        await ctx.respond(embed=embed)

    @slash_command()
    async def pause(self, ctx: MusicApplicationContext) -> None:
        """Pauses current song."""

        try:
            ensure_voice_state(ctx, requires_song=True, no_live_notice=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.respond("⏯ **Paused** song, use **/**`resume` to **continue**.")
            return
        await ctx.respond("❌ The **song** is **already paused**.")

    @slash_command()
    async def resume(self, ctx: MusicApplicationContext) -> None:
        """Resumes the current song."""

        try:
            ensure_voice_state(ctx, no_live_notice=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.respond("⏯ **Resumed** song, use **/**`pause` to **pause**.")
            return
        await ctx.respond("❌ Either is the **song is not paused**, **or nothing** is currently **playing**.")

    @slash_command()
    async def volume(self, ctx: MusicApplicationContext, percent: int) -> None:
        """Sets the volume of the current song."""

        try:
            ensure_voice_state(ctx, requires_song=True, no_live_notice=True)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        if not (0 < percent <= 100):
            if percent > 100:
                await ctx.respond("❌ **Volume** cannot be **larger than 100%**.")
            elif percent <= 0:
                await ctx.respond("❌ **Volume** has to be **larger than 0%**. Use **/**`pause` pause.")
            return

        before: int = int(ctx.voice_state.current.source.volume * 100)
        ctx.voice_state.current.source.volume = percent / 100
        emoji: str = "🔈" if percent < 50 else "🔉" if percent == 50 else "🔊"
        await ctx.respond(f"{emoji} **Set volume** of song from {before}% **to {percent}%**")

    @slash_command()
    async def lyrics(self, ctx: MusicApplicationContext,
                     song: Optional[str] = None, artist: Optional[str] = None) -> None:
        """Search for lyrics, default search is current song."""
        await ctx.defer()

        try:
            response = get_lyrics(song or ctx.voice_state.current.source.title,
                                  artist or ctx.voice_state.current.source.uploader)

            embed = Embed(title="Lyrics", description=response[0], colour=0xFF0000)
            embed.set_author(name=f"{response[2]} by {response[3]}", icon_url=response[1])
            await ctx.respond(embed=embed)
        except (AttributeError, HTTPException):
            await ctx.respond("❌ **Can not find any lyrics** for that song.")

    @slash_command()
    async def history(self, ctx: MusicApplicationContext) -> None:
        """Latest played songs in the current session."""

        if not len(ctx.voice_state.history):
            await ctx.respond("❌ There is **no data in** this **session**.")
            return

        embed: Embed = Embed(title="History", description="Latest played songs in this session.\n\n", colour=0xFF0000)
        for i, item in enumerate(ctx.voice_state.history, start=1):
            embed.description += f"`{i}`. {item}\n"
        await ctx.respond(embed=embed)

    @slash_command()
    async def session(self, ctx: MusicApplicationContext) -> None:
        """Receive current session ID to hotkey control music."""

        try:
            ctx.voice_state.add_control(ctx.author.id)
        except ValueError as e:
            await ctx.respond(str(e))
            return

        embed: Embed = Embed(
            title="__Secret__ ID", color=0xFF0000,
            description="This ID is personalized and should therefore **only be used by you**.\n"
                        "Sharing isn't caring, **sharing is __dangerous__**.")

        ip: str = SETTINGS["BetterMusicControlListenOnIP"]
        port: int = SETTINGS["BetterMusicControlListenOnPort"]
        session_id: str = f"`{ip}:{port}?{ctx.voice_state.id}={ctx.voice_state.session[ctx.author.id][0]}`"
        embed.add_field(name="Session ID", value=session_id, inline=False)
        embed.add_field(name="Software",
                        value="BetterMusicControl is not installed yet?\n"
                              "Get it [here](https://github.com/staubtornado/BetterMusicControl/releases/latest).")
        try:
            await ctx.author.send(embed=embed)
        except Forbidden:
            await ctx.respond("❌ **Failed** to send. Please **check if** your **DMs are open**.")
            return
        await ctx.respond("📨 **Sent** the **__secret__ ID** for the current session **to your DMs**.")


def setup(bot: CustomBot) -> None:
    bot.add_cog(Music(bot))
