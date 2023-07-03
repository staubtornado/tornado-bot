from random import randint

from discord import Message, slash_command, Option, Member, Forbidden, HTTPException, File, MessageType, NotFound
from discord.ext.commands import Cog
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from bot import TornadoBot
from lib.contexts import CustomApplicationContext
from lib.db.db_classes import LevelingStats
from lib.leveling.calculation import xp_to_level
from lib.leveling.leaderboard import gen_leaderboard
from lib.leveling.level_up import generate_level_up_card
from lib.leveling.rank_card import generate_rank_card


class Leveling(Cog):
    def __init__(self, bot: TornadoBot) -> None:
        self.bot = bot
        self._limiter = Limiter(
            RequestRate(1, Duration.MINUTE)
        )

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return
        if not message.guild:
            return
        # Check if slash command
        if message.type == MessageType.application_command:
            return

        stats: LevelingStats = await self.bot.database.get_leveling_stats(message.author.id, message.guild.id)
        if not stats:
            stats = LevelingStats(message.guild.id, message.author.id, 0, 0)
        xp, level = xp_to_level(stats.experience)

        try:
            async with self._limiter.ratelimit(f"{message.author.id}:{message.guild.id}"):
                pass
        except BucketFullException:
            pass
        else:
            xp_add: int = randint(15, 25)
            stats.experience += xp_add

            if xp_to_level(stats.experience)[1] > level:
                try:
                    avatar: bytes = await message.author.avatar.read()
                except AttributeError:
                    avatar: bytes = await message.author.default_avatar.read()
                except (NotFound, HTTPException):
                    return

                try:
                    await message.channel.send(
                        file=await generate_level_up_card(stats, avatar, message.author.name),
                        delete_after=60,
                        content=message.author.mention
                    )
                except (Forbidden, HTTPException):
                    pass
        finally:
            stats.message_count += 1
            await self.bot.database.set_leveling_stats(stats)

    @slash_command()
    async def leaderboard(
            self,
            ctx: CustomApplicationContext,
            page: Option(int, "The page to view.", required=False, default=1)
    ) -> None:
        """Shows the leaderboard for the current guild."""

        await ctx.defer()
        offset: int = (page - 1) * 19
        _leaderboard: list[LevelingStats] = await self.bot.database.get_guild_leaderboard(ctx.guild.id, limit=19, offset=offset)
        if not _leaderboard:
            await ctx.respond("❌ **No leaderboard** found for this guild.")
            return

        # Get the avatars of the users
        avatars: list[bytes] = []
        user_names: list[str] = []
        leaderboard: list[LevelingStats] = []

        for stats in _leaderboard:
            user = ctx.guild.get_member(stats.user_id)
            if not user:
                await self.bot.database.remove_leveling_stats(stats.user_id, ctx.guild.id)
                continue

            try:
                avatar = await user.avatar.read()
            except AttributeError:
                avatar = await user.default_avatar.read()
            except (NotFound, HTTPException):
                continue

            avatars.append(avatar)
            user_names.append(user.name)
            leaderboard.append(stats)

        # Generate the leaderboard card and send it
        cards: list[File] = await gen_leaderboard(leaderboard, avatars, user_names, ctx.guild.name, page)
        await ctx.respond(file=cards[0])
        await ctx.send(file=cards[1]) if len(cards) > 1 else None

    @slash_command()
    async def rank(
            self,
            ctx: CustomApplicationContext,
            user: Option(Member, "The user to view.", required=False, default=None)
    ) -> None:
        """Shows the rank of a user."""
        await ctx.defer()

        user = user or ctx.author
        stats: LevelingStats = await self.bot.database.get_leveling_stats(user.id, ctx.guild.id)
        if not stats:
            await ctx.respond("❌ **No stats** found for this user.")
            return

        # Calculate the rank of the user in the guild.
        # Get the leaderboard for the guild
        leaderboard: list[LevelingStats] = await self.bot.database.get_guild_leaderboard(ctx.guild.id)
        # Get the index of the user in the leaderboard
        rank: int = leaderboard.index(stats) + 1

        # Calculate the rank of the user globally.
        # Get the global leaderboard
        leaderboard_global: list[LevelingStats] = (await self.bot.database.get_global_leaderboard(-1))[rank:]

        # Get the index of the user in the global leaderboard, binary search
        rank_global: int = 0
        start: int = 0
        end: int = len(leaderboard_global) - 1
        while start <= end:
            mid: int = (start + end) // 2
            if leaderboard_global[mid] == stats:
                rank_global = mid + 1
                break
            elif leaderboard_global[mid] > stats:
                end = mid - 1
            else:
                start = mid + 1

        # Generate the rank card and send it
        card: File = await generate_rank_card(stats, user, rank, rank_global + rank)
        await ctx.respond(file=card)


def setup(bot: TornadoBot) -> None:
    bot.add_cog(Leveling(bot))
