from json import loads
from os import listdir
from os.path import exists
from random import choice, random
from urllib.parse import urlparse

from discord import Bot, ApplicationContext, Embed, Option, AutocompleteContext, SlashCommandGroup
from discord.ext.commands import Cog
from requests import get, Response
from tqdm import tqdm

from data.config.settings import SETTINGS
from lib.images.processing import ping


async def get_categories(ctx: AutocompleteContext = None) -> list:
    rtrn = []

    if ctx is None or ctx.bot.get_channel(ctx.interaction.channel_id).is_nsfw():
        rtrn.extend(["porn", "ass", "asian", "masturbation", "shaved", "close-up", "pussy", "boobs", "milf"])
    rtrn.extend(["meme"])
    return rtrn


class Images(Cog):
    """
    View images from the most popular subreddits on Reddit. Image editing following soon.
    """

    def __init__(self, bot: Bot):
        self.bot = bot

        self.categories = {"porn": "Pornhub", "ass": "ass", "asian": "AsiansGoneWild",
                           "masturbation": "Fingering", "shaved": "shavedpussies", "close-up": "closeup",
                           "pussy": "pussy", "cat": "cats", "boobs": "tits", "milf": "milf", "meme": "dankmemes"}
        self.gallery = {}
        for category in tqdm(self.categories, "Scraping image urls"):
            for response in dict(loads(self.request(subreddit=self.categories[category]).text))["memes"]:
                try:
                    self.gallery[category]
                except KeyError:
                    self.gallery[category] = []
                self.gallery[category].append(response)

    def request(self, subreddit: str = "dankmemes", count: int = 50) -> Response:
        return get(f"https://meme-api.herokuapp.com/gimme/{subreddit}/{count}")

    async def send(self, ctx: ApplicationContext, category: str, nsfw: bool = True):
        if nsfw and not ctx.channel.is_nsfw():
            await ctx.respond("🔞 This command **requires** an **NSFW** channel.", ephemeral=True)
            return
        await ctx.defer()

        content = choice(self.gallery[category])
        title = content["title"]
        source = content["postLink"]
        url = content["url"]
        votes = content["ups"]
        embed: Embed = Embed(title=title, colour=SETTINGS["Colours"]["Default"],
                             description=f"[Source]({source}) | {votes} votes")
        embed.set_image(url=url)
        embed.set_footer(text=f"Provided by {urlparse(url).netloc}")
        await ctx.respond(embed=embed)

    image: SlashCommandGroup = SlashCommandGroup(name="image", description="Create or get images from the web.")

    @image.command()
    async def random(self, ctx: ApplicationContext,
                     category: Option(str, "Choose a category from which the bot selects an image.",
                                      autocomplete=get_categories)):
        """Random image from a given category."""

        categories = {"porn": True, "ass": True, "asian": True, "masturbation": True, "shaved": True, "close-up": True,
                      "pussy": True, "cat": True, "boobs": True, "milf": True, "meme": False}

        if category == "pussy":
            if not random() > 0.3:
                category = "cat"
        await self.send(ctx, category, nsfw=categories[category])

    @image.command()
    async def ping(self, ctx: ApplicationContext):
        """Fool everyone by adding a ping to your guild icon."""
        await ctx.defer()

        if f"{ctx.guild.id}.png" not in listdir("./data/cache"):
            try:
                if not exists(f"./data/cache/{ctx.guild_id}"):
                    await ctx.guild.icon.save(f"./data/cache/{ctx.guild.id}.png")
            except AttributeError:
                await ctx.respond("❌ This **guild has no icon**.")
                return
        path, file = ping(f"./data/cache/{ctx.guild.id}.png")

        embed: Embed = Embed(title="@everyone", colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=path)
        await ctx.respond(embed=embed, file=file)


def setup(bot: Bot):
    bot.add_cog(Images(bot))
