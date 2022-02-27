from asyncio import sleep
from random import randint
from sqlite3 import Cursor

from discord import slash_command, ApplicationContext, Message, Bot
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from data.db.memory import database

on_cooldown: list = []


class ExperienceSystem:
    def __init__(self, bot: Bot, message: Message):
        self.bot = bot
        self.message = message

        self.min_xp = SETTINGS["Cogs"]["Experience"]["MinXP"]
        self.max_xp = SETTINGS["Cogs"]["Experience"]["MaxXP"]
        self.multiplier = SETTINGS["Cogs"]["Experience"]["Multiplication"]
        self.cooldown = SETTINGS["Cogs"]["Experience"]["Cooldown"]
        self.base_level = SETTINGS["Cogs"]["Experience"]["BaseLevel"]

        self.xp = None
        self.level = None

    async def get_xp(self) -> int:
        return -1

    async def start(self) -> bool:
        if self.message.author.bot or self.message.guild is None:
            return False

        await self.add_xp()

        return True

    async def add_xp(self) -> None:
        cur: Cursor = database.cursor()

        cur.execute(f"""
            SELECT Messages from experience where (GuildID, UserID) = (
                {self.message.guild.id}, {self.message.author.id})
        """)
        row: int = cur.fetchone()

        if row is None:
            cur.execute(f"""
                INSERT INTO experience (GuildID, UserID) VALUES ({self.message.guild.id}, {self.message.author.id})
            """)

        cur.execute(f"""UPDATE experience SET Messages = Messages + 1 
                        WHERE (GuildID, UserID) = ({self.message.guild.id}, {self.message.author.id})""")
        database.commit()

        if not (self.message.guild.id, self.message.author.id) in on_cooldown:
            xp: int = round(randint(self.min_xp, self.max_xp) * self.multiplier)

            self.check_for_level_up()

            cur.execute(f"""UPDATE experience SET XP = XP + {xp}
                            WHERE (GuildID, UserID) = ({self.message.guild.id}, {self.message.author.id})""")
            database.commit()
            on_cooldown.append((self.message.guild.id, self.message.author.id))
            await sleep(self.cooldown)
            on_cooldown.remove((self.message.guild.id, self.message.author.id))

    def calc_xp(self) -> int:
        return round(self.base_level * 1.1248 ** self.level)

    def check_for_level_up(self) -> tuple:
        required: int = self.calc_xp()

        while self.xp >= required:
            self.xp -= required
            self.level += 1
            required = self.calc_xp()
        return self.xp, self.level


class Experience(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext):
        pass

    @slash_command()
    async def rank(self, ctx: ApplicationContext):
        pass


def setup(bot):
    bot.add_cog(Experience(bot))
