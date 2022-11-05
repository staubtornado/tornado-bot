from discord import ApplicationContext

from lib.music.music_application_context import MusicApplicationContext
from lib.music.prepared_source import PreparedSource
from lib.music.voicestate import VoiceState


class CustomApplicationContext(ApplicationContext):
    voice_state: VoiceState
    priority: bool = False


def ensure_voice_state(ctx: MusicApplicationContext, **kwargs) -> None:
    if ctx.author.voice is None and not kwargs.get("no_voice_required"):
        raise ValueError("❌ **You are not** connected to a **voice** channel.")

    if ctx.voice_client:
        if ctx.voice_client.channel != ctx.author.voice.channel:
            raise ValueError(f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}.")

    if ctx.voice_state.live and kwargs.get("no_live_notice"):
        raise ValueError(
            "❌ **Not available while playing** a **live** stream.\n"
            "❔Execute **/**`stop` to **switch to default song streaming**."
        )

    if not ctx.voice_state.is_playing and kwargs.get("requires_song"):
        raise ValueError("❌ **Nothing** is currently **playing**.")
    if ctx.voice_state.current and (isinstance(ctx.voice_state.current.source, PreparedSource) and
                                    (kwargs.get("requires_song") or kwargs.get("no_processing"))):
        raise ValueError("❌ Next **song is** currently **processing**, please **wait**.")

    if not len(ctx.voice_state.queue) and kwargs.get("requires_queue"):
        raise ValueError("❌ The **queue** is **empty**.")

    if ctx.voice_state.processing and kwargs.get("no_processing"):
        raise ValueError("⚠ I am **currently processing** the previous **request**.")
