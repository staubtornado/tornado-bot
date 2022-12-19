from aiohttp import ClientSession
from discord import slash_command, ApplicationContext, Embed
from discord.ext.commands import Cog

from bot import CustomBot
from data.config.settings import SETTINGS


class Images(Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot

    @slash_command(name="image", description="Get a random image from a subreddit.")
    async def image(self, ctx: ApplicationContext, subreddit: str) -> None:
        """Get a random image from a subreddit."""
        await ctx.defer()

        async with ClientSession() as session:
            async with session.get(f"https://meme-api.com/gimme/{subreddit}/") as r:
                data = await r.json()
        if data["nsfw"] and not ctx.channel.is_nsfw():
            await ctx.respond("🔞 This **subreddit contains NSFW** content, which is **not allowed in this channel**.")
            return

        embed: Embed = Embed(title=data["title"], description=data["postLink"], colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=data["url"])
        await ctx.respond(embed=embed)

    @slash_command()
    async def meme(self, ctx: ApplicationContext) -> None:
        """Get a random meme."""
        await ctx.defer()

        for i in range(3):
            async with ClientSession() as session:
                async with session.get("https://meme-api.com/gimme/") as r:
                    data = await r.json()
            if data["nsfw"] and not ctx.channel.is_nsfw():
                continue
            break
        else:
            await ctx.respond("❌ Failed to get a meme. Try again later.")
            return

        embed: Embed = Embed(title=data["title"], description=data["postLink"], colour=SETTINGS["Colours"]["Default"])
        embed.set_image(url=data["url"])
        await ctx.respond(embed=embed)


def setup(bot: CustomBot) -> None:
    bot.add_cog(Images(bot))
