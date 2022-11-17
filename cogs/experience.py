from asyncio import sleep
from random import randint
from sqlite3 import Cursor
from typing import Optional

from discord import Bot, Member, Message, slash_command, ApplicationContext
from discord.ext.commands import Cog
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.experience.calculation import level_size, total_xp
from lib.experience.gen_leaderboard import generate_leaderboard_card
from lib.experience.gen_lvl_up_card import generate_lvl_up_card
from lib.experience.gen_rank_card import generate_rank_card
from lib.experience.stats import ExperienceStats
from lib.utils.utils import binary_search

MIN: int = SETTINGS["Cogs"]["Experience"]["MinXP"]
MAX: int = SETTINGS["Cogs"]["Experience"]["MaxXP"]


class Experience(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.limiter = Limiter(
            RequestRate(1, Duration.MINUTE)
        )

        #  Used to determine ranking in rank command.
        self._leaderboards: dict[int, list[int]] = {}

    @staticmethod
    async def _calc_leaderboard(guild_id: int) -> list[int]:
        cur: Cursor = database.cursor()
        cur.execute(
            """SELECT XP, Level FROM experience WHERE GuildID = ?""",
            (guild_id,)
        )

        leaderboard: list[int] = []
        for result in cur.fetchall():
            leaderboard.append(total_xp(result[0], result[1]))
            await sleep(0)
        leaderboard.sort()
        return leaderboard

    async def cog_before_invoke(self, ctx: ApplicationContext) -> None:
        await ctx.defer()
        self._leaderboards[ctx.guild_id] = await self._calc_leaderboard(ctx.guild_id)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.author.bot:
            return

        cur: Cursor = database.cursor()
        cur.execute(
            """INSERT OR IGNORE INTO experience (GuildID, UserID) VALUES (?, ?)""",
            (message.guild.id, message.author.id)
        )
        cur.execute(
            """SELECT ExpIsActivated, ExpMultiplication FROM settings WHERE GuildID = ?""",
            (message.guild.id,)
        )

        data: tuple[int, int] = cur.fetchone()
        if not data[0]:
            return
        multiplier: int = round(data[1])

        cur.execute(
            """SELECT XP, Level, Messages FROM experience WHERE (GuildID, UserID) = (?, ?)""",
            (message.guild.id, message.author.id)
        )
        xp, level, messages = cur.fetchone()

        try:
            self.limiter.try_acquire(str((message.guild.id, message.author.id)))
        except BucketFullException:
            return
        else:
            xp += randint(MIN, MAX) * multiplier
            while xp >= level_size(level):
                xp -= level_size(level)
                level += 1

                if not xp >= level_size(level):
                    stats: ExperienceStats = ExperienceStats({
                        "xp": xp,
                        "total": total_xp(xp, level),
                        "level": level,
                        "member": message.author,
                        "message_count": messages
                    })
                    await message.reply(file=await generate_lvl_up_card(stats), delete_after=60)
        finally:
            messages += 1
            cur.execute(
                """UPDATE experience SET (XP, Level, Messages) = (?, ?, ?) WHERE (GuildID, UserID) = (?, ?)""",
                (xp, level, messages, message.guild.id, message.author.id)
            )
            database.commit()

    @slash_command()
    async def rank(self, ctx: ApplicationContext, user: Optional[Member] = None) -> None:
        target: Member = user or ctx.author
        if target.bot:
            await ctx.respond("❌ This **user is not available**.")
            return

        cur: Cursor = database.cursor()
        cur.execute(
            """SELECT ExpIsActivated FROM settings WHERE GuildID = ?""",
            (ctx.guild_id,)
        )
        if not cur.fetchone()[0]:
            await ctx.respond("❌ Level system is **not yet enabled on this server**.")
            return

        cur.execute(
            """SELECT XP, Level, Messages FROM experience WHERE (GuildID, UserID) = (?, ?)""",
            (target.guild.id, target.id)
        )
        data: Optional[tuple[int, int, int]] = cur.fetchone()
        if data is None:
            data = 0, 0, 0
        xp, level, messages = data
        rank: int = binary_search(
            arr=self._leaderboards.get(ctx.guild_id),
            x=total_xp(xp, level),
            s=0,
            r=len(self._leaderboards.get(ctx.guild_id)) - 1
        )

        stats: ExperienceStats = ExperienceStats({
            "xp": xp,
            "total": total_xp(xp, level),
            "level": level,
            "member": target,
            "message_count": messages,
            "rank": len(self._leaderboards.get(ctx.guild_id)) - rank
        })
        await ctx.respond(file=await generate_rank_card(stats))

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext, page: int = 1) -> None:
        cur: Cursor = database.cursor()
        cur.execute(
            """SELECT ExpIsActivated FROM settings WHERE GuildID = ?""",
            (ctx.guild_id,)
        )
        if not cur.fetchone()[0]:
            await ctx.respond("❌ Level system is **not yet enabled on this server**.")
            return

        cur.execute(
            """SELECT XP, Level, UserID FROM experience WHERE GuildID = ?""",
            (ctx.guild_id,)
        )
        table: list[tuple[int, int, int]] = cur.fetchall()
        table.sort(key=lambda _row: total_xp(_row[0], _row[1]), reverse=True)

        result: list[ExperienceStats] = []
        start: int = (page - 1) * SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        end: int = start + SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        for row in table[start:end]:
            member: Optional[Member] = ctx.guild.get_member(row[2])

            if member is None or member.bot:
                cur.execute(
                    """DELETE FROM experience WHERE (GuildID, UserID) = (?, ?)""",
                    (ctx.guild_id, row[2])
                )
                continue

            result.append(ExperienceStats({
                "member": member,
                "xp": row[0],
                "level": row[1],
                "total": total_xp(row[0], row[1])
            }))

        if not len(result):
            await ctx.respond("❌ **Nothing here** yet.")
            return
        await ctx.respond(files=await generate_leaderboard_card(result))


def setup(bot: Bot) -> None:
    bot.add_cog(Experience(bot))
