from asyncio import sleep
from math import ceil
from random import randint
from sqlite3 import Cursor

from discord import slash_command, ApplicationContext, Message, Bot, Embed, Member
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.utils.utils import ordinal

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
        self._valid = False

        try:
            self._cur.execute(f"""
                SELECT XP, Level, Messages from experience where (GuildID, UserID) = (?, ?)
            """, (self.message.guild.id, self.message.author.id))
        except AttributeError:
            return
        self._valid = True

        try:
            self.xp, self.level, self.messages = self._cur.fetchone()
        except TypeError:
            if isinstance(message, Message):
                self._cur.execute("""INSERT INTO experience (GuildID, UserID) VALUES (?, ?)""",
                                  (self.message.guild.id, self.message.author.id))
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
        if not self._valid:
            return False
        if self.message.author.bot or self.message.guild is None:
            return False
        await self.add_xp()
        return True

    async def add_xp(self) -> None:
        self._cur.execute("""SELECT XP, Level from experience where (GuildID, UserID) = (?, ?)""",
                          (self.message.guild.id, self.message.author.id))

        self._cur.execute("""UPDATE experience SET Messages = Messages + 1 WHERE (GuildID, UserID) = (?, ?)""",
                          (self.message.guild.id, self.message.author.id))
        database.commit()

        if not (self.message.guild.id, self.message.author.id) in on_cooldown:
            self.xp += round(randint(self.min_xp, self.max_xp) * self.multiplier)
            await self.check_for_level_up()
            self._cur.execute("""UPDATE experience SET (XP, Level) = (?, ?) WHERE (GuildID, UserID) = (?, ?)""",
                              (self.xp, self.level, self.message.guild.id, self.message.author.id))

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

        try:
            embed.add_field(name="Level", value=f"`{system.get_level()}`")
            embed.add_field(name="Total XP", value=f"`{system.total_xp()}`")
            embed.add_field(name="Messages", value=f"`{system.get_messages()}`")
            embed.add_field(name=f"{system.get_xp()} / {system.calc_xp()} XP", value=system.progress_bar())
        except TypeError:
            await ctx.respond("❌ I **do not have** any **information about you or this user**.")
            return

        try:
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        except AttributeError:
            embed.set_author(name=ctx.author, icon_url=ctx.author.default_avatar.url)
        await ctx.respond(embed=embed)

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext, *, page: int = 1):
        """Displays the most active users on this server."""
        await ctx.defer()

        cur: Cursor = database.cursor()
        cur.execute("""SELECT UserID, Level, XP from experience where GuildID = ?""", [ctx.guild.id])

        total_xps: list = []
        data: list = []
        user_list: list = []

        system: ExperienceSystem = ExperienceSystem(self.bot, ctx)
        for i, row in enumerate(cur.fetchall()):
            system.level = row[1]
            system.xp = row[2]
            total_xp: int = system.total_xp()

            if total_xp == 0:
                continue
            if row[0] == ctx.author.id:
                ctx.position = i

            total_xps.append(total_xp)
            total_xps.sort()

            index: int = total_xps.index(total_xp)
            user_list.insert(index, row[0])
            data.insert(index, (row[1], row[2]))
        user_list.reverse()
        data.reverse()

        items_per_page = SETTINGS["Cogs"]["Experience"]["Leaderboard"]["ItemsPerPage"]
        pages: int = ceil(len(user_list) / items_per_page)

        start: int = (page - 1) * items_per_page
        end: int = start + items_per_page

        if page > pages or page < 1:
            await ctx.respond(f"❌ **Invalid** page.")
            return

        def get_author_position() -> str:
            try:
                position: int = ctx.position
            except AttributeError:
                return ""
            return f"\n{ctx.author.mention} has the {ordinal(position + 1)} position in the leaderboard."

        embed: Embed = Embed(title="Leaderboard", description="Most active users on this server. Use **/**`rank @user` "
                                                              f"to get more information.{get_author_position()}",
                             colour=SETTINGS["Colours"]["Default"])
        for i, user_id in enumerate(user_list[start:end], start=start):
            embed.add_field(name=f"{i + 1}. {self.bot.get_user(user_id)}",
                            value=f"Level: `{data[i][0]}` XP: `{data[i][1]}`")
        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Experience(bot))
