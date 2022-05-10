from discord import Bot, slash_command, ApplicationContext
from discord.ext.commands import Cog

from lib.currency.wallet import Wallet


# Concept:
# Every user has a global balance and a tab that shows the revenue on the current server
# They can buy roles, channels, messages, advertisement, users aso with their global balance on every server
# Every transaction gives a small percentage to the global bank and to the guild-bank for the specific server
# User can claim their money by executing a command every day /claim [daily | monthly | special] for example
# Users are limited to a specific amount of transactions per server every day and have a daily global limit
# Every stat is public, but only the user themselves can see their accurate stats. Others only see estimations
# Every bot has it own economy, meaning that self-hosted versions cannot access the official economy
# Users can livest their balance: Daily revenue is linear and investments can be percentage increases


class Currency(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def wallet(self, ctx: ApplicationContext):
        """Displays information about your wallet."""

        wallet: Wallet = Wallet(ctx.author)
        await ctx.respond(embed=wallet.create_embed())


def setup(bot: Bot):
    bot.add_cog(Currency(bot))
