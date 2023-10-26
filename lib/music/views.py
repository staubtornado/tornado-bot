from asyncio import QueueFull

from discord import Interaction, ButtonStyle
from discord.ui import View, Button
from lib.contexts import CustomApplicationContext
from lib.db.db_classes import Emoji
from lib.enums import AudioPlayerLoopMode
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

        if audio_player.full:
            raise QueueFull('Queue is full')
        free: int = 200 - len(audio_player)

        parts: int = min(tracks.total // free, 22)
        remainder: int = tracks.total % free

        for i in range(0, parts):
            self.add_item(
                Button(
                    style=ButtonStyle.green,
                    label=f'{i * free + 1} - {(i + 1) * free}',
                    custom_id=random_hex(8),
                )
            )

        if remainder > 0:
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
        if interaction.user.id == self.ctx.author.id:
            self.disable_all_items()

            for button in self.children:
                if isinstance(button, Button) and button.custom_id == interaction.custom_id:
                    self.value: str = button.label
            emoji_checkmark: Emoji = await self.ctx.bot.database.get_emoji("checkmark")
            await interaction.response.edit_message(
                content=f"{emoji_checkmark} **You choose**: `{self.value}`",
                view=None
            )
            self.stop()
            return True
        return False

    async def on_check_failure(self, interaction: Interaction) -> None:
        emoji_cross: Emoji = await self.ctx.bot.database.get_emoji("cross")
        await interaction.response.send_message(
            f'{emoji_cross} Only the command author can use this.',
            ephemeral=True
        )


class LoopView(View):
    def __init__(self, ctx: CustomApplicationContext, audio_player: AudioPlayer) -> None:
        super().__init__(timeout=15)
        self.ctx = ctx
        self.audio_player = audio_player
        self.value = None

        self.add_item(
            Button(
                style=ButtonStyle.green,
                label='Loop Queue',
                custom_id=random_hex(8)
            )
        )
        self.add_item(
            Button(
                style=ButtonStyle.green,
                label='Loop Track',
                custom_id=random_hex(8)
            )
        )
        self.add_item(
            Button(
                style=ButtonStyle.red,
                label='Cancel',
                custom_id=random_hex(8)
            )
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id == self.ctx.author.id:
            self.disable_all_items()

            for button in self.children:
                if isinstance(button, Button) and button.custom_id == interaction.custom_id:
                    if button.label == 'Loop Queue':
                        self.audio_player.loop = AudioPlayerLoopMode.QUEUE
                    else:
                        self.audio_player.loop = AudioPlayerLoopMode.SONG
                    self.value: str = button.label
                    break

            emoji_checkmark: Emoji = await self.ctx.bot.database.get_emoji("checkmark")
            await interaction.response.edit_message(
                content=f"{emoji_checkmark} **You choose**: `{self.value}`",
                view=None
            )
            self.stop()
            return True
        return False

    async def on_check_failure(self, interaction: Interaction) -> None:
        emoji_cross: Emoji = await self.ctx.bot.database.get_emoji("cross")
        await interaction.response.send_message(
            f'{emoji_cross} Only the command author can use this.',
            ephemeral=True
        )


class SearchOptions(View):
    def __init__(self, ctx: CustomApplicationContext, amount: int = 5) -> None:
        super().__init__(timeout=20)
        self.ctx = ctx
        self.index = None

        for i in range(1, amount + 1):
            self.add_item(
                Button(
                    style=ButtonStyle.green,
                    label=f'{i}',
                    custom_id=random_hex(8)
                )
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id == self.ctx.author.id:
            self.disable_all_items()

            for button in self.children:
                if isinstance(button, Button) and button.custom_id == interaction.custom_id:
                    self.index = int(button.label) - 1

            emoji_checkmark: Emoji = await self.ctx.bot.database.get_emoji("checkmark")
            await interaction.response.edit_message(
                content=f"{emoji_checkmark} **You choose**: `{self.index + 1}`",
                view=None,
                embed=None
            )
            self.stop()
            return True
        return False

    async def on_check_failure(self, interaction: Interaction) -> None:
        emoji_cross: Emoji = await self.ctx.bot.database.get_emoji("cross")
        await interaction.response.send_message(
            f'{emoji_cross} Only the command author can use this.',
            ephemeral=True
        )
