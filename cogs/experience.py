from random import randint
from sqlite3 import Cursor
from typing import Optional

from discord import Bot, Member, Message, slash_command, ApplicationContext
from discord.ext.commands import Cog
from pyrate_limiter import Limiter, RequestRate, Duration, BucketFullException

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.experience.gen_leaderboard import generate_leaderboard_card
from lib.experience.gen_lvl_up_card import generate_lvl_up_card
from lib.experience.gen_rank_card import generate_rank_card
from lib.experience.level_size import level_size
from lib.experience.stats import ExperienceStats

MIN: int = SETTINGS["Cogs"]["Experience"]["MinXP"]
MAX: int = SETTINGS["Cogs"]["Experience"]["MaxXP"]


class Experience(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.limiter = Limiter(
            RequestRate(1, Duration.MINUTE)
        )

    @staticmethod
    def get_stats(member: Member) -> ExperienceStats:
        ...

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
            (message.guild.id, )
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
                level += 1

                stats: ExperienceStats = ExperienceStats({
                    "xp": xp,
                    "total": level_size(level),
                    "level": level,
                    "member": message.author,
                    "message_count": messages
                })
                if not xp >= level_size(level):
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
        await ctx.defer()

        target: Member = user or ctx.author

        if target.bot:
            await ctx.respond("❌ **Bots are not available**.")
            return

        cur: Cursor = database.cursor()
        cur.execute(
            """INSERT OR IGNORE INTO experience (GuildID, UserID) VALUES (?, ?)""",
            (target.guild.id, target.id)
        )
        cur.execute(
            """SELECT XP, Level, Messages FROM experience WHERE (GuildID, UserID) = (?, ?)""",
            (target.guild.id, target.id)
        )
        xp, level, messages = cur.fetchone()

        stats: ExperienceStats = ExperienceStats({
            "xp": xp,
            "total": level_size(level),
            "level": level,
            "member": target,
            "message_count": messages
        })
        await ctx.respond(file=await generate_rank_card(stats))

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext, page: int = 1) -> None:
        await ctx.defer()

        cur: Cursor = database.cursor()
        cur.execute(
            """SELECT UserID, XP, Level FROM experience WHERE GuildID = ?""",
            (ctx.guild_id, )
        )
        table: list[tuple[int, int, int]] = cur.fetchall()
        table.sort(key=lambda _row: level_size(_row[2]) + _row[1], reverse=True)

        result: list[ExperienceStats] = []
        start: int = (page - 1) * SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        end: int = start + SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        for row in table[start:end]:
            result.append(ExperienceStats({
                "member": ctx.guild.get_member(row[0]),
                "xp": row[1],
                "level": row[2]
            }))

        if not len(table):
            response: str = "❌ **Nothing here** yet."

            if ctx.author.guild_permissions.manage_guild:
                response += "\n❔ **Enable leveling** with **/**`settings experience`."
            await ctx.respond(response)
            return
        await ctx.respond(files=await generate_leaderboard_card(result))


def setup(bot: Bot) -> None:
    bot.add_cog(Experience(bot))
