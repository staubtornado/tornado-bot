from asyncio import StreamReader, StreamWriter, start_server
from json import loads, JSONDecodeError
from typing import Union, Any, Callable

from discord import Bot, Cog, User, Embed
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from data.config.settings import SETTINGS
from lib.music.song import SongStr
from lib.music.voicestate import VoiceState


class ControlRequest:
    __slots__ = ("session", "requester", "action", "_data")

    session: VoiceState
    requester: User
    action: str
    _data: dict[str, str]

    def __init__(self, data: dict[str, str], voice_states: dict[int, VoiceState]):
        self._data: dict[str, str] = data
        if len(data) != 3:
            raise ValueError("Data does not match required pattern.")

        for guild_vs_id in voice_states:
            if voice_states[guild_vs_id].id == data.get("sessionID").split("=")[0]:
                self.session: VoiceState = voice_states[guild_vs_id]
                break
        else:
            raise ValueError("Session ID is invalid.")

        self.requester: Union[User, None] = self.session.bot.get_user(int(data.get("uID")))
        if self.requester is None or self.requester.id not in self.session.registered_controls or \
                self.session.registered_controls[self.requester.id] != data.get("sessionID").split("=")[1]:
            raise ValueError("Missing permissions or invalid user.")

        self.action: str = data.get("message")
        if data.get("message") not in ["TOGGLE", "FETCH"]:
            raise ValueError("Invalid request.")


class BetterMusicControlReceiver:
    bot: Bot
    voice_states: dict[int, VoiceState]
    _limiter: Limiter

    def __init__(self, bot: Bot):
        self.bot = bot
        bot.loop.create_task(self.run_server())

        self._limiter = Limiter(RequestRate(3, Duration.SECOND * 5))  # 3 requests per 5 seconds

    async def handle_data(self, reader: StreamReader, writer: StreamWriter) -> None:
        """Called everytime a connection is established."""

        data: bytes = await reader.read(1024)
        address, port = writer.get_extra_info("peername")
        print(f"[NETWORK] Accepting connection from {address}:{port}")

        try:
            self.voice_states
        except AttributeError:
            music: Union[Any, Cog] = self.bot.get_cog("Music")
            self.voice_states = music.voice_states

        while data != b"END":
            try:
                info: dict[str, str] = dict(loads(data.decode().replace("'", '"')))
                request: ControlRequest = ControlRequest(data=info, voice_states=self.voice_states)
            except (ValueError, AttributeError, JSONDecodeError) as e:
                print(data, "----------------------", e)

                print(f"[NETWORK] Received invalid request from {address}:{port}")
                writer.write(bytes(str(e), "utf-8"))
                await writer.drain()
                break

            try:
                self._limiter.try_acquire(address)
            except BucketFullException as e:
                print(f"[NETWORK] Received rate-limited request from {address}:{port}")
                writer.write(bytes(str(e), "utf-8"))
                await writer.drain()
                break

            print(f"[NETWORK] Received request from {address}:{port}")
            if request.action == "TOGGLE":
                action: dict[bool, tuple[Callable, str]] = {
                    True: (request.session.voice.pause, "Paused"), False: (request.session.voice.resume, "Resumed")}
                embed: Embed = Embed(color=0xFF0000)

                try:
                    embed.set_author(name=request.requester, icon_url=request.requester.avatar.url)
                except AttributeError:
                    embed.set_author(name=request.requester, icon_url=request.requester.default_avatar)
                embed.description = f"️⏯ **{action.get(request.session.voice.is_playing())[1]}** over hotkey-control."

                action.get(request.session.voice.is_playing())[0]()
                await request.session.channel_send(embed=embed)

            if request.action == "FETCH":
                response: dict[str, Union[str, None]]

                try:
                    if isinstance(request.session.current, SongStr):
                        response = {
                            "title": request.session.current.title,
                            "uploader": request.session.current.uploader,
                            "url": "#",
                            "thumbnail": "https://dummyimage.com/600x400/4cc2ff/0011ff.jpg&text=No+thumbnail."
                        }
                    else:
                        response = {
                            "title": request.session.current.source.title_limited_embed,
                            "uploader": request.session.current.source.uploader,
                            "url": request.session.current.source.url,
                            "thumbnail": request.session.current.source.thumbnail
                        }
                except AttributeError:
                    response = {
                        "title": "",
                        "uploader": "",
                        "url": "",
                        "thumbnail": ""
                    }

                try:
                    writer.write(bytes(str(response), "utf-8"))
                    await writer.drain()
                except (ConnectionResetError, OSError):
                    break
            try:
                data = await reader.read(1024)
            except (ConnectionResetError, OSError):
                break

        print(f"[NETWORK] Closing connection to {address}:{port}")

        try:
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            return

    async def run_server(self) -> None:
        server = await start_server(self.handle_data, SETTINGS["BetterMusicControlListenOnIP"],
                                    SETTINGS["BetterMusicControlListenOnPort"])
        print(f"[NETWORK] Listening on {SETTINGS['BetterMusicControlListenOnIP']}:"
              f"{SETTINGS['BetterMusicControlListenOnPort']}")
        async with server:
            await server.serve_forever()
