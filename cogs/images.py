from asyncio import run
from random import choice, random
from urllib.parse import urlparse

from discord import Bot, slash_command, ApplicationContext, Embed
from discord.ext.commands import Cog
from tqdm import tqdm

from data.config.settings import SETTINGS
from lib.images.scraping import ImageScraping


class Images(Cog):
    def __init__(self, bot: Bot):
        self.gallery: dict = {}
        self.bot = bot
        run(self.create_gallery())

    async def create_gallery(self):
        categories: list = ["babe", "teen", "ass", "asian", "masturbation", "shaved", "close-up", "pussy",
                            "cat-pictures", "natural-tits", "milf", "meme", "porn-gif"]

        self.gallery.clear()
        for category in tqdm(categories, "Scraping image urls"):
            url: str = f"https://www.pornpics.de/{category}/"
            if category == "cat-pictures":
                url = "https://www.rd.com/list/cat-pictures/"
            if category == "meme":
                url = "https://www.pinterest.de/Mcnicollke/meme-page/"
            if category == "porn-gif":
                url = "https://gifsex.blog/24-teen-sex-gifs.html"
            self.gallery[category] = ImageScraping(url).get_all_images()

    async def send(self, ctx: ApplicationContext, category: str, message: str, nsfw: bool = True):
        if nsfw and not ctx.channel.is_nsfw():
            await ctx.respond("🔞 This command **requires** an **NSFW** channel.")
            return
        await ctx.defer()

        url = choice(self.gallery[category])
        embed: Embed = Embed(title=message, colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=url)
        embed.set_footer(text=f"Provided by {urlparse(url).netloc}")
        print(url)
        await ctx.respond(embed=embed)

    @slash_command()
    async def porn(self, ctx: ApplicationContext, gif: bool = False):
        """Sends a porn image. Requires NSFW channel."""
        if not gif:
            await self.send(ctx, "babe", "Here, take that porn!")
            return
        await self.send(ctx, "porn-gif", "More frames? You're welcome.")

    @slash_command()
    async def teen(self, ctx: ApplicationContext):
        """Sends a teen (>18) porn image. Requires NSFW channel."""
        await self.send(ctx, "teen", "Why is the FBI here?")

    @slash_command()
    async def ass(self, ctx: ApplicationContext):
        """Sends an ass porn image. Requires NSFW channel."""
        await self.send(ctx, "ass", "Here, take some booty.")

    @slash_command()
    async def asian(self, ctx: ApplicationContext):
        """Sends an asian porn image. Requires NSFW channel."""
        await self.send(ctx, "asian", "Asian hate does not exist.")

    @slash_command()
    async def masturbation(self, ctx: ApplicationContext):
        """Sends a masturbation porn image. Requires NSFW channel."""
        await self.send(ctx, "masturbation", "Maybe the opposite of you?")

    @slash_command()
    async def shaved(self, ctx: ApplicationContext):
        """Sends a shaved pussy image. Requires NSFW channel."""
        await self.send(ctx, "shaved", "That looks clean.")
        
    @slash_command()
    async def closeup(self, ctx: ApplicationContext):
        """Sends a closeup image of a pussy. Requires NSFW channel."""
        await self.send(ctx, "close-up", "4K UHD Ultra High Quality")

    @slash_command()
    async def pussy(self, ctx: ApplicationContext):
        """Sends a pussy image. Requires NSFW channel."""
        if random() > 0.3:
            await self.send(ctx, "pussy", "Take that pussy.")
            return
        await self.send(ctx, "cat-pictures", "Take that pussy.")

    @slash_command()
    async def boob(self, ctx: ApplicationContext):
        """Sends a boob image. Requires NSFW channel."""
        await self.send(ctx, "natural-tits", "Take that boobs.")

    @slash_command()
    async def milf(self, ctx: ApplicationContext):
        """Sends a milf image. Requires NSFW channel."""
        await self.send(ctx, "milf", "Hey mom!")

    #####################################################################

    @slash_command()
    async def meme(self, ctx: ApplicationContext):
        """Sends a (hopefully) funny meme."""
        await self.send(ctx, "meme", "Here we go.", nsfw=False)


def setup(bot: Bot):
    bot.add_cog(Images(bot))
