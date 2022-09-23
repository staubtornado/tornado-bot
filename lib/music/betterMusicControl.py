from ast import literal_eval
from asyncio import StreamReader, StreamWriter, start_server
from typing import Union, Any

from discord import Bot, Cog, User
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from data.config.settings import SETTINGS
from lib.music.voicestate import VoiceState


class RateLimitedError(Exception):
    pass


class ControlRequest:
    session: VoiceState
    requester: User
    action: str

    def __init__(self, data: dict[str, Union[str, int]], voice_states: dict[int, VoiceState]):
        self._data: dict[str, Union[str, int]] = data
        if len(data) != 3:
            raise ValueError("Data does not match required pattern.")

        for guild_vs_id in voice_states:
            if voice_states[guild_vs_id].id == data.get("sessionID").split("=")[0]:
                self.session = voice_states[guild_vs_id]
                break
        else:
            raise ValueError("Session ID is invalid.")

        self.requester: Union[User, None] = self.session.bot.get_user(data.get("uID"))
        if self.requester is None or self.requester.id not in self.session.registered_controls or \
                self.session.registered_controls[self.requester.id] != data.get("sessionID").split("=")[1]:
            raise ValueError("Missing permissions or invalid user.")

        self.action: str = data.get("message")
        if data.get("message") != "TOGGLE":  # Will later be replaced with list[str] when there are more than one types.
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
                request = ControlRequest(data=literal_eval(data.decode()), voice_states=self.voice_states)
            except (ValueError, RateLimitedError) as e:
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
                if request.session.voice.is_playing():
                    request.session.voice.pause()
                    await request.session.channel_send(message=f"Paused by {request.requester.mention}")
                else:
                    request.session.voice.resume()
                    await request.session.channel_send(
                        message=f"Resumed by {request.requester.mention}")

        print(f"[NETWORK] Closing connection to {address}:{port}")
        await writer.wait_closed()

    async def run_server(self) -> None:
        server = await start_server(self.handle_data, SETTINGS["BetterMusicControlListenOnIP"],
                                    SETTINGS["BetterMusicControlListenOnPort"])
        async with server:
            await server.serve_forever()
