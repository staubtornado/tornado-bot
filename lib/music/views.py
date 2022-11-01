from asyncio import QueueFull
from typing import Any, Callable

from discord import ButtonStyle, Interaction
from discord.ui import View, button as ui_button, Button

from data.config.settings import SETTINGS
from lib.music.music_application_context import MusicApplicationContext
from lib.music.other import ensure_voice_state
from lib.music.prepared_source import PreparedSource
from lib.music.song import Song
from lib.music.voicestate import Loop


class VariableButton(Button):
    def __init__(self, custom_id, callback: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_id = custom_id
        self.callback = callback


class LoopDecision(View):
    def __init__(self, ctx: MusicApplicationContext):
        super().__init__()
        self.ctx = ctx

    @ui_button(
        label="Song",
        style=ButtonStyle.green,
        custom_id="678354926"
    )
    async def song(self, button: Button, interaction: Interaction) -> None:
        try:
            ensure_voice_state(self.ctx, requires_song=True)
        except ValueError as e:
            await interaction.response.edit_message(content=str(e), view=None)
            return

        if self.ctx.voice_state.loop == Loop.NONE:
            self.ctx.voice_state.loop = Loop.SONG
            message: str = "🔁 **Looped song**, use **/**`loop` to **disable** loop."
        else:
            self.ctx.voice_state.loop = Loop.NONE
            message: str = "🔁 **Unlooped song**, use **/**`loop` to **enable** loop."
        await interaction.response.edit_message(
            content=message,
            view=None
        )

    @ui_button(
        label="Queue",
        style=ButtonStyle.blurple,
        custom_id="790243817"
    )
    async def queue(self, button: Button, interaction: Interaction):
        try:
            ensure_voice_state(self.ctx, requires_song=True)
        except ValueError as e:
            await interaction.response.edit_message(content=str(e), view=None)
            return

        if self.ctx.voice_state.queue.duration > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
            await interaction.response.edit_message(
                content="❌ The **queue is too long** to be looped.",
                view=None
            )
            return

        if self.ctx.voice_state.loop == Loop.QUEUE:
            self.ctx.voice_state.loop = Loop.NONE
            message: str = f"🔁 **Unlooped queue**, use **/**`loop` to **enable** loop."
        else:
            self.ctx.voice_state.loop = Loop.QUEUE
            try:
                self.ctx.voice_state.queue.put_nowait(Song(PreparedSource(
                    self.ctx.voice_state.current.source.ctx,
                    {"title": self.ctx.voice_state.current.source.title,
                     "uploader": self.ctx.voice_state.current.source.uploader,
                     "duration": self.ctx.voice_state.current.source.duration,
                     "url": self.ctx.voice_state.current.source.url}
                )))
            except QueueFull:
                pass
            message: str = f"🔁 **Looped queue**, use **/**`loop` to **disable** loop."
        await interaction.response.edit_message(
            content=message,
            view=None
        )


class PlaylistParts(View):
    def __init__(self):
        super().__init__(timeout=15)
        self.value = None

    async def callback(self, interaction: Interaction):
        self.children: list[Any, Button] = self.children
        for child in self.children:
            if child.custom_id == interaction.custom_id:
                self.value = child.label

        if self.value == "Help me choose.":
            length = str(self.children[0].label).split(' - ')
        else:
            length = str(self.value).split(' - ')
        await interaction.response.edit_message(
            content=f"✅ Added **{int(length[1]) + 1 - int(length[0])} songs**.", view=None)
        self.stop()
