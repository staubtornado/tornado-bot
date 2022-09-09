from discord import ButtonStyle, Interaction
from discord.ui import View, button as ui_button, Button

from data.config.settings import SETTINGS
from lib.music.other import CustomApplicationContext, ensure_voice_state
from lib.music.song import SongStr


class LoopDecision(View):
    def __init__(self, ctx: CustomApplicationContext):
        super().__init__()
        self.ctx = ctx

    @ui_button(
        label="Song",
        style=ButtonStyle.green,
        custom_id="678354926"
    )
    async def song(self, button: Button, interaction: Interaction):
        instance = ensure_voice_state(self.ctx, requires_song=True)
        if isinstance(instance, str):
            await interaction.response.edit_message(content=instance, view=None)
            return

        self.ctx.voice_state.loop = not self.ctx.voice_state.loop
        if self.ctx.voice_state.loop:
            await interaction.response.edit_message(content="🔁 **Looped song**, use **/**`loop` to **disable** loop.",
                                                    view=None)
            return
        await interaction.response.edit_message(content="🔁 **Unlooped song**, use **/**`loop` to **enable** loop.",
                                                view=None)
        return

    @ui_button(
        label="Queue",
        style=ButtonStyle.blurple,
        custom_id="790243817"
    )
    async def queue(self, button: Button, interaction: Interaction):
        instance = ensure_voice_state(self.ctx, requires_queue=True, no_processing=True)
        if isinstance(instance, str):
            await interaction.response.edit_message(content=instance, view=None)
            return

        if self.ctx.voice_state.songs.get_duration() > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
            await interaction.response.edit_message(content="❌ The **queue is too long** to be looped.",
                                                    view=None)
            return

        self.ctx.voice_state.iterate = not self.ctx.voice_state.iterate
        if self.ctx.voice_state.iterate:
            await self.ctx.voice_state.songs.put(SongStr(self.ctx.voice_state.current, self.ctx))

            await interaction.response.edit_message(content=f"🔁 **Looped queue**, use **/**`loop` to **disable** "
                                                            f"loop.",
                                                    view=None)
            return
        await interaction.response.edit_message(content=f"🔁 **Unlooped queue**, use **/**`loop` to **enable** loop.",
                                                view=None)
