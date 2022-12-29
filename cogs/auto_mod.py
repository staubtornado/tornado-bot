from datetime import timedelta, datetime
from re import compile as re_compile, Pattern
from typing import AnyStr

from discord import Message, Embed, Color
from discord.ext.commands import Cog
from emoji import emoji_count
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from bot import CustomBot
from lib.db.data_objects import GuildSettings


class AutoMod(Cog):
    _limiter: Limiter
    _action_limiter: Limiter

    _regex_custom_emojis: Pattern[AnyStr]
    _regex_discord_invite: Pattern[AnyStr]
    _regex_mentions: Pattern[AnyStr]

    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self._limiter = Limiter(  # For message cooldown
            RequestRate(3, Duration.SECOND * 5)
        )
        self._action_limiter = Limiter(  # For performing actions
            RequestRate(2, Duration.MINUTE * 30)
        )

        self._regex_custom_emojis = re_compile(r"<a?:\w+:\d+>")
        self._regex_discord_invite = re_compile(r"(https://)?discord\.gg/[A-Za-z\d]+")
        self._regex_mentions = re_compile(r"<@!?(\d+)>")

    @staticmethod
    def _check_uppercase(message: Message) -> None:
        """Checks if >=70% of the message is written in uppercase."""
        if len(message.content) < 6:
            return
        if sum(1 for c in message.content if c.isupper()) / len(message.content) >= 0.7:
            raise Exception(f"**Deleted message** from %s **for spamming.**")

    def _check_invite(self, message: Message) -> None:
        if self._regex_discord_invite.match(message.content.strip()):
            raise Exception(f"**Deleted message** from %s **for sending an invite.**")

    def _check_mentions(self, message: Message) -> None:
        if len(self._regex_mentions.findall(message.content)) > 5:
            raise Exception(f"**Deleted message** from %s **for mentioning too many people.**")

    def _check_emojis(self, message: Message) -> None:
        standard_emojis: int = emoji_count(message.content)
        custom_emojis: int = len(self._regex_custom_emojis.findall(message.content))

        if standard_emojis + custom_emojis > 5:
            raise Exception(f"**Deleted message** from %s **for spamming emojis.**")

    @staticmethod
    async def _check_repeated_message(message: Message) -> None:
        if len(message.content) < 6:
            return
        async for msg in message.channel.history(limit=5):
            if msg.content == message.content and message.id != msg.id:
                raise Exception(f"**Deleted message** from %s **for spamming.**")

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.author.bot:
            return

        settings: GuildSettings = await self.bot.database.get_guild_settings(message.guild)
        if settings.auto_mod_level == 0:
            return
        if message.author.guild_permissions.manage_guild:
            return

        try:
            try:  # Check if the user is on cooldown
                self._limiter.try_acquire(str(message.author.id))
            except BucketFullException:
                raise Exception(f"**Deleted message** from %s **for spamming.**")

            # Perform other checks
            self._check_uppercase(message)
            self._check_mentions(message)
            self._check_emojis(message)
            self._check_invite(message)
            await self._check_repeated_message(message)
        except Exception as e:
            reason: Exception = e
        else:
            return

        try:
            self._action_limiter.try_acquire(str(message.author.id))
        except BucketFullException:
            reason = Exception("**Timed out** %s due to **3 violations within 30 minutes.**")
            await message.author.timeout(datetime.utcnow() + timedelta(minutes=30))
        else:
            await message.reply(content=reason.args[0] % message.author.mention, delete_after=10)
        await message.delete()
        if not settings.generate_audit_log:
            return

        if channel := self.bot.get_channel(settings.audit_log_channel_id):
            embed: Embed = Embed(
                title="AutoMod",
                description=reason.args[0] % message.author.mention,
                color=Color.orange(),
                timestamp=message.created_at
            )
            await channel.send(embed=embed)
            return
        settings.generate_audit_log = False
        settings.audit_log_channel_id = None
        await self.bot.database.update_guild_settings(settings)


def setup(bot: CustomBot) -> None:
    bot.add_cog(AutoMod(bot))
