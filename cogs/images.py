from random import choice, random

from discord import Bot, slash_command, ApplicationContext, Embed
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from lib.images.images import ImageSystem


class Images(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @classmethod
    async def send(cls, ctx: ApplicationContext, url: str, message: str):
        if not ctx.channel.is_nsfw():
            await ctx.respond("This command requires an NSFW channel.")
            return
        await ctx.defer()

        image_url: str = choice(ImageSystem(url).get_all_images())

        embed: Embed = Embed(title=message, colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=image_url)
        embed.set_footer(text="Provided by HQPornPhotos")
        await ctx.respond(embed=embed)

    @slash_command()
    async def porn(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/young/", "Here, take that porn!")

    @slash_command()
    async def teen(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/teen/", "Why is the FBI here?")

    @slash_command()
    async def ass(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/young-ass/", "Here, take some booty.")

    @slash_command()
    async def japanese(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/japanese/", "Omae wa mou shindeiru. Nani?")

    @slash_command()
    async def masturbation(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/masturbation/", "Maybe the opposite of you?")

    @slash_command()
    async def shaved(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/shaved/", "That looks clean.")
        
    @slash_command()
    async def closeup(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/close-up/", "4K UHD Ultra High Quality")

    @slash_command()
    async def pussy(self, ctx: ApplicationContext):
        if random() > 0.3:
            await self.send(ctx, "http://www.hqpornphotos.com/young-pussy/", "Take that pussy.")
            return
        await self.send(ctx, "https://www.pexels.com/search/cat/", "Take that pussy.")

    @slash_command()
    async def boob(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/perfect-tits/", "Take that boobs.")

    @slash_command()
    async def jackpot(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/beauty/", "Woooooooooh!")

    @slash_command()
    async def milf(self, ctx: ApplicationContext):
        await self.send(ctx, "http://www.hqpornphotos.com/milf/", "Hey mom!")


def setup(bot: Bot):
    bot.add_cog(Images(bot))
