from asyncio import sleep
from random import randint
from sqlite3 import Cursor

from discord import slash_command, ApplicationContext, Message, Bot, Embed, Member, User, Colour
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from data.db.memory import database

on_cooldown: list = []


class ExperienceSystem:
    def __init__(self, bot: Bot, message: ApplicationContext or Message):
        self.bot = bot
        self.message = message

        self.min_xp = SETTINGS["Cogs"]["Experience"]["MinXP"]
        self.max_xp = SETTINGS["Cogs"]["Experience"]["MaxXP"]
        self.multiplier = SETTINGS["Cogs"]["Experience"]["Multiplication"]
        self.cooldown = SETTINGS["Cogs"]["Experience"]["Cooldown"]
        self.base_level = SETTINGS["Cogs"]["Experience"]["BaseLevel"]

        self.xp = None
        self.level = None
        self.messages = None

        self._cur: Cursor = database.cursor()

        self._cur.execute(f"""
            SELECT XP, Level, Messages from experience where (GuildID, UserID) = (
                {self.message.guild.id}, {self.message.author.id})
        """)

        try:
            self.xp, self.level, self.messages = self._cur.fetchone()
        except TypeError:
            self._cur.execute(f"""
                    INSERT INTO experience (GuildID, UserID) VALUES ({self.message.guild.id}, {self.message.author.id})
                """)
            self.xp = 0
            self.level = 0
            self.messages = 0
            database.commit()

    def get_xp(self) -> int:
        return self.xp

    def get_level(self) -> int:
        return self.level

    def get_messages(self) -> int:
        return self.messages

    async def start(self) -> bool:
        if self.message.author.bot or self.message.guild is None:
            return False
        await self.add_xp()
        return True

    async def add_xp(self) -> None:
        self._cur.execute(f"""
            SELECT XP, Level from experience where (GuildID, UserID) = (
                {self.message.guild.id}, {self.message.author.id})
        """)

        self._cur.execute(f"""UPDATE experience SET Messages = Messages + 1 
                        WHERE (GuildID, UserID) = ({self.message.guild.id}, {self.message.author.id})""")
        database.commit()

        if not (self.message.guild.id, self.message.author.id) in on_cooldown:
            self.xp += round(randint(self.min_xp, self.max_xp) * self.multiplier)
            await self.check_for_level_up()
            self._cur.execute(f"""UPDATE experience SET (XP, Level) = ({self.xp}, {self.level})
                            WHERE (GuildID, UserID) = ({self.message.guild.id}, {self.message.author.id})""")

            database.commit()
            on_cooldown.append((self.message.guild.id, self.message.author.id))
            await sleep(self.cooldown)
            on_cooldown.remove((self.message.guild.id, self.message.author.id))

    def calc_xp(self, level=None) -> int:
        if level is None:
            level = self.level
        return round(self.base_level * 1.1248 ** level)

    def total_xp(self) -> int:
        xp: int = 0

        for i in range(self.level):
            xp += self.calc_xp(level=i)
        return xp + self.xp

    def progress_bar(self) -> str:
        percent = (self.xp / self.calc_xp()) * 100
        return round(percent / 10) * "◻️" + round((100 - percent) / 10) * "▪️"

    async def check_for_level_up(self) -> None:
        required: int = self.calc_xp()

        level_up: bool = False
        while self.xp >= required:
            self.xp -= required
            self.level += 1
            level_up = True
            required = self.calc_xp()
        if level_up:
            embed = Embed(title="Level Up!", description=f"GG, you are now level {self.level} on this server.",
                          colour=SETTINGS["Colours"]["Default"])
            embed.add_field(name=f"Progress ({self.xp}XP / {required}XP)", value=self.progress_bar())
            embed.set_author(name=self.message.author.name, icon_url=self.message.author.avatar.url)
            await self.message.reply(embed=embed, delete_after=60)


class Experience(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def rank(self, ctx: ApplicationContext, user: Member = None):
        """Displays information about your stats on this server."""
        await ctx.defer()

        if user is not None:
            ctx.author = user
        system: ExperienceSystem = ExperienceSystem(self.bot, ctx)

        embed = Embed(colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="Total XP", value=f"`{system.total_xp()}`")
        embed.add_field(name="Level", value=f"`{system.get_level()}`")
        embed.add_field(name="Messages", value=f"`{system.get_messages()}`")
        embed.add_field(name=f"Progress ({system.get_xp()}XP / {system.calc_xp()}XP)", value=system.progress_bar())

        try:
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
        except AttributeError:
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.default_avatar.url)
        await ctx.respond(embed=embed)

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext):
        query: str = f"""SELECT UserID, Level, XP from experience where GuildID = {ctx.guild.id}"""

        cur: Cursor = database.cursor()
        cur.execute(query)

        total_xps: list = []
        user_list: list = []

        system: ExperienceSystem = ExperienceSystem(self.bot, ctx)
        for i, row in enumerate(cur.fetchall()):
            system.level = row[1]
            system.xp = row[2]
            total_xp: int = system.total_xp()

            total_xps.append(total_xp)
            total_xps.sort()
            user_list.insert(total_xps.index(total_xp), row[0])

            if i >= 24:
                break

        embed: Embed = Embed(title="Leaderboard", description="Top 25 users on this server. Use **/**`rank [@user]` "
                                                              "to get more information.", colour=Colour.blue())
        for i, user_id in enumerate(user_list):
            embed.add_field(name=f"{i + 1}. {await self.bot.fetch_user(user_id)}", value="0")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Experience(bot))
