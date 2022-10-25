from discord import ApplicationContext

from lib.music.voicestate import VoiceState


class MusicApplicationContext(ApplicationContext):
    voice_state: VoiceState
    priority: bool
