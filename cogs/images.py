from random import choice, random

from discord import Bot, slash_command, ApplicationContext, Embed
from discord.ext import tasks
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from lib.images.images import ImageSystem


class Images(Cog):
    def __init__(self, bot: Bot):
        self.gallery: dict = {}
        self.bot = bot
        self.update_gallery.start()

    def cog_unload(self):
        self.update_gallery.cancel()

    @tasks.loop(minutes=SETTINGS["DatabaseSyncInSeconds"])
    async def update_gallery(self):
        categories: list = ["babe", "teen", "ass", "asian", "masturbation", "shaved", "close-up", "pussy",
                            "cat-pictures", "natural-tits", "milf"]

        self.gallery.clear()
        for category in categories:
            url: str = f"https://www.pornpics.de/{category}/"
            if category == "cat-pictures":
                url = "https://www.rd.com/list/cat-pictures/"

            images: list = await ImageSystem(url).get_all_images()
            self.gallery[category] = images

    async def send(self, ctx: ApplicationContext, category: str, message: str):
        if not ctx.channel.is_nsfw():
            await ctx.respond("This command requires an NSFW channel.")
            return
        await ctx.defer()

        embed: Embed = Embed(title=message, colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=choice(self.gallery[category]))
        embed.set_footer(text="Provided by PornPics")
        await ctx.respond(embed=embed)

    @slash_command()
    async def porn(self, ctx: ApplicationContext):
        await self.send(ctx, "babe", "Here, take that porn!")

    @slash_command()
    async def teen(self, ctx: ApplicationContext):
        await self.send(ctx, "teen", "Why is the FBI here?")

    @slash_command()
    async def ass(self, ctx: ApplicationContext):
        await self.send(ctx, "ass", "Here, take some booty.")

    @slash_command()
    async def asian(self, ctx: ApplicationContext):
        await self.send(ctx, "asian", "Omae wa mou shindeiru. Nani?")

    @slash_command()
    async def masturbation(self, ctx: ApplicationContext):
        await self.send(ctx, "masturbation", "Maybe the opposite of you?")

    @slash_command()
    async def shaved(self, ctx: ApplicationContext):
        await self.send(ctx, "shaved", "That looks clean.")
        
    @slash_command()
    async def closeup(self, ctx: ApplicationContext):
        await self.send(ctx, "close-up", "4K UHD Ultra High Quality")

    @slash_command()
    async def pussy(self, ctx: ApplicationContext):
        if random() > 0.3:
            await self.send(ctx, "pussy", "Take that pussy.")
            return
        await self.send(ctx, "cat-pictures", "Take that pussy.")

    @slash_command()
    async def boob(self, ctx: ApplicationContext):
        await self.send(ctx, "natural-tits", "Take that boobs.")

    @slash_command()
    async def milf(self, ctx: ApplicationContext):
        await self.send(ctx, "milf", "Hey mom!")


def setup(bot: Bot):
    bot.add_cog(Images(bot))