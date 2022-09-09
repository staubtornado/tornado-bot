from typing import Union

from discord import ApplicationContext

from lib.music.song import SongStr
from lib.music.voicestate import VoiceState


class CustomApplicationContext(ApplicationContext):
    voice_state: VoiceState
    priority: bool = False


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
