from re import sub
from typing import Optional

from discord import Guild, TextChannel, SelectOption, Interaction
from discord.ui import Select, View

from bot import CustomBot


class TextChannelDropdown(Select):
    def __init__(self, bot: CustomBot, guild: Guild):
        self.bot = bot
        self.guild = guild

        options = []

        for channel in guild.channels:
            if isinstance(channel, TextChannel):
                select_option = SelectOption(
                    label=f"{channel.name} ({channel.id})",
                )
                options.append(select_option)

        super().__init__(
            placeholder="Choose a text channel...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        channel: Optional[TextChannel] = None

        for _channel in interaction.guild.channels:
            if _channel.id != int(sub(r".*\(|\)", "", self.values[0])):
                continue
            channel = _channel

            settings = await self.bot.database.get_guild_settings(interaction.guild)
            settings.audit_log_channel = channel.id
            await self.bot.database.update_guild_settings(settings)
            break

        if not channel:
            await interaction.response.send_message(
                f"❌ An error occurred while setting up. Try again later.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"📢 {channel.mention} **will** now **receive activity logs**.",
                ephemeral=True
            )
        self.view.stop()


class DropdownView(View):
    def __init__(self, bot: CustomBot, guild: Guild):
        self.bot = bot
        super().__init__()

        self.add_item(TextChannelDropdown(self.bot, guild))
