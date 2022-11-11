from re import sub
from sqlite3 import Cursor
from typing import Optional

from discord import Bot, Guild, TextChannel, SelectOption, Interaction
from discord.ui import Select, View

from data.db.memory import database


class TextChannelDropdown(Select):
    def __init__(self, bot: Bot, guild: Guild):
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

            cur: Cursor = database.cursor()
            cur.execute(
                """INSERT OR IGNORE INTO settings (GuildID) VALUES (?)""",
                (interaction.guild_id,)
            )
            cur.execute(
                """UPDATE settings SET (GenerateAuditLog, AuditLogChannel) = (?, ?) WHERE GuildID = ?""",
                (1, _channel.id, interaction.guild_id)
            )
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
    def __init__(self, bot: Bot, guild: Guild):
        self.bot = bot
        super().__init__()

        self.add_item(TextChannelDropdown(self.bot, guild))
