from discord import Interaction, ButtonStyle
from discord.ui import View, Button
from lib.contexts import CustomApplicationContext
from lib.music.audio_player import AudioPlayer

from lib.spotify.track_collection import TrackCollection
from lib.utils import random_hex


class QueueFill(View):
    def __init__(self, ctx: CustomApplicationContext, tracks: TrackCollection, audio_player: AudioPlayer) -> None:
        super().__init__(timeout=15)
        self.value = None

        self.ctx = ctx
        self.tracks = tracks
        self.audio_player = audio_player


        free: int = 200 - len(audio_player)

        if free < 1:
            raise ValueError('Queue is full')
        
        parts: int = tracks.total // free
        remainder: int = tracks.total % free

        for i in range(0, parts):
            self.add_item(
                Button(
                    style=ButtonStyle.green,
                    label=f'{i * free + 1} - {(i + 1) * free}',
                    custom_id=random_hex(8),
                )
            )
        self.add_item(
            Button(
                style=ButtonStyle.green,
                label=f'{parts * free + 1} - {parts * free + remainder}',
                custom_id=random_hex(8),
            )
        )
        self.add_item(
            Button(
                style=ButtonStyle.blurple,
                label='Help me decide.',
                custom_id=random_hex(8)
            )
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id

    async def on_timeout(self) -> None:
        await self.ctx.response.edit_message(
            content='You took too long to respond.',
            view=None
        )
