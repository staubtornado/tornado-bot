from random import randint
from typing import Optional

from discord import Member, Message, slash_command, ApplicationContext
from discord.ext.commands import Cog
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from bot import CustomBot
from data.config.settings import SETTINGS
from lib.db.data_objects import GuildSettings, ExperienceStats
from lib.experience.calculation import xp_to_level
from lib.experience.gen_leaderboard import generate_leaderboard_card
from lib.experience.gen_lvl_up_card import generate_lvl_up_card
from lib.experience.gen_rank_card import generate_rank_card

MIN: int = SETTINGS["Cogs"]["Experience"]["MinXP"]
MAX: int = SETTINGS["Cogs"]["Experience"]["MaxXP"]


class Experience(Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self.limiter = Limiter(
            RequestRate(1, Duration.MINUTE)
        )

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.author.bot:
            return

        settings: GuildSettings = await self.bot.database.get_guild_settings(message.guild)
        if not settings.xp_is_activated:
            return
        stats: ExperienceStats = await self.bot.database.get_member_stats(message.author)

        try:
            self.limiter.try_acquire(str((message.guild.id, message.author.id)))
        except BucketFullException:
            return
        else:
            stats.total += randint(MIN, MAX) * settings.xp_multiplier
            if xp_to_level(stats.total)[0] > stats.level:
                stats.level += 1
                await message.reply(
                    file=await generate_lvl_up_card(stats),
                    delete_after=60
                )
        finally:
            stats.message_amount += 1
            await self.bot.database.update_leaderboard(stats)

    @slash_command()
    async def rank(self, ctx: ApplicationContext, user: Optional[Member] = None) -> None:
        """Shows the rank of a user."""

        target: Member = user or ctx.author
        if target.bot:
            await ctx.respond("❌ This **user is not available**.")
            return
        await ctx.defer()

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild)
        if not settings.xp_is_activated:
            await ctx.respond("❌ Level system is **not yet enabled on this server**.")
            return

        stats: ExperienceStats = await self.bot.database.get_member_stats(target)
        if stats is None:
            await ctx.respond("❌ This **user has no stats**.")
            return
        await ctx.respond(file=await generate_rank_card(stats))

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext, page: int = 1) -> None:
        """Shows the leaderboard of the server."""
        await ctx.defer()

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild)
        if not settings.xp_is_activated:
            await ctx.respond("❌ Level system is **not yet enabled on this server**.")
            return

        start: int = (page - 1) * SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        end: int = start + SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        leaderboard: list[ExperienceStats] = (await self.bot.database.get_leaderboard(ctx.guild))
        if not leaderboard:
            await ctx.respond("❌ The **leaderboard** is **empty**.")
            return
        _max_pages: int = len(leaderboard) // SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"] + 1
        if not 0 < page <= _max_pages:
            await ctx.respond(f"❌ **Invalid page**. Must be **between 1 and {_max_pages}**.")
            return
        await ctx.respond(files=await generate_leaderboard_card(
            leaderboard[start:end],
            (page, len(leaderboard) // SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"] + 1)
        ))


def setup(bot: CustomBot) -> None:
    bot.add_cog(Experience(bot))
