from asyncio import run
from random import choice, random
from urllib.parse import urlparse

from discord import Bot, slash_command, ApplicationContext, Embed, Option, AutocompleteContext
from discord.ext.commands import Cog
from tqdm import tqdm

from data.config.settings import SETTINGS
from lib.images.scraping import ImageScraping


async def get_categories(ctx: AutocompleteContext) -> list:
    rtrn = []

    if ctx.bot.get_channel(ctx.interaction.channel_id).is_nsfw():
        rtrn.extend(["Porn", "Porn-Gif", "Teen", "Ass", "Asian", "Masturbation", "Shaved", "Close-Up", "Pussy",
                     "Boobs", "Milf"])
    rtrn.extend(["Meme"])
    return rtrn


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
            await ctx.respond("🔞 This command **requires** an **NSFW** channel.", ephemeral=True)
            return
        await ctx.defer()

        url = choice(self.gallery[category])
        embed: Embed = Embed(title=message, colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=url)
        embed.set_footer(text=f"Provided by {urlparse(url).netloc}")
        await ctx.respond(embed=embed)

    @slash_command()
    async def image(self, ctx: ApplicationContext,
                    category: Option(str, "Choose a category from which the bot selects an image.",
                                     autocomplete=get_categories)):
        """Select a category from wich the bot will send a random image."""

        categories = {"Porn": ("babe", "Here, take that porn!"), "Teen": ("teen", "Why is the FBI here?"),
                      "Ass": ("ass", "Here, take some booty."), "Asian": ("asian", "Asian hate does not exist."),
                      "Masturbation": ("masturbation", "Maybe the opposite of you?"),
                      "Shaved": ("shaved", "That looks clean."), "Close-Up": ("close-up", "4K UHD Ultra High Quality"),
                      "Pussy": ("pussy", "Take that pussy."), "cat": ("cat-pictures", "Take that pussy."),
                      "Boobs": ("natural-tits", "Take that boobs."), "Milf": ("milf", "Hey mom!"),
                      "Meme": ("meme", "Here we go.", False), "Porn-Gif": ("porn-gif", "More frames? You're welcome.")}

        if category == "Pussy":
            if not random() > 0.3:
                category = "cat"

        try:
            nsfw = categories[category][2]
        except IndexError:
            nsfw = True
        await self.send(ctx, categories[category][0], categories[category][1], nsfw=nsfw)


def setup(bot: Bot):
    bot.add_cog(Images(bot))
