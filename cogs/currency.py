from typing import Union

from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Role, \
    CategoryChannel, TextChannel, StageChannel, VoiceChannel, Guild, Embed
from discord.ext.commands import Cog
from discord.utils import basic_autocomplete

from lib.currency.bank import Bank
from lib.currency.wallet import Wallet


# Concept:
# Every user has a global balance and a tab that shows the revenue on the current server
# They can buy roles, channels, messages, advertisement, users aso with their global balance on every server
# Every transaction gives a small percentage to the global bank and to the guild-bank for the specific server
# User can claim their money by executing a command every day /claim [daily | monthly | special] for example
# Users are limited to a specific amount of transactions per server every day and have a daily global limit
# Every stat is public, but only the user themselves can see their accurate stats. Others only see estimations
# Every bot has it own economy, meaning that self-hosted versions cannot access the official economy
# Users can invest their balance: Daily revenue is linear and investments can be percentage increases
from lib.currency.wallstreet import Wallstreet


def get_claim_options(ctx: AutocompleteContext) -> list:
    return ["Daily", "Monthly", "Special"]


class Currency(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.wallstreet = None
        self.banks = {}

    def get_bank(self, guild: Guild):
        return self.banks[guild.id]

    def get_wallet(self, guild: Guild, member: Member) -> Wallet:
        return self.banks[guild.id].wallets[member.id]

    async def cog_before_invoke(self, ctx: ApplicationContext):
        if self.wallstreet is None:
            self.wallstreet = Wallstreet(self.bot)

        try:
            self.banks[ctx.guild.id]
        except KeyError:
            self.banks[ctx.guild.id] = Bank(ctx.guild)
        except AttributeError:
            return

        try:
            self.banks[ctx.guild.id].wallets[ctx.author.id]
        except KeyError:
            for bank in self.banks:
                try:
                    self.banks[bank].wallets[ctx.author.id]
                except KeyError:
                    continue
                else:
                    self.banks[ctx.guild.id].wallets[ctx.author.id] = self.banks[bank].wallets[ctx.author.id]
                    break
            self.banks[ctx.guild.id].wallets[ctx.author.id] = Wallet(ctx.author)

    @slash_command()
    async def wallet(self, ctx: ApplicationContext, *, user: Member = None):
        """Displays information about your wallet."""
        await ctx.defer()
        if ctx.guild.owner not in [ctx.author, user]:
            await ctx.respond(embed=self.get_wallet(ctx.guild, ctx.author).create_embed(estimated=bool(user)))
            return
        await ctx.respond(embed=self.get_bank(ctx.guild).wallet.create_embed(estimated=bool(user)))

        wallet: Wallet = Wallet(ctx.author, target=user)
        await ctx.respond(embed=wallet.create_embed())

    @slash_command()
    async def claim(self, ctx: ApplicationContext,
                    offer: Option(str, "Choose what you want to claim. Options might vary.",
                                  autocomplete=basic_autocomplete(get_claim_options), required=True)):
        """Claim your current offers."""
        await ctx.defer()
        wallet = self.get_wallet(ctx.guild, ctx.author)

        if offer == "Daily":
            wallet.add_money(100)

            await ctx.respond("Here are 100 Coins.")
            return
        if offer == "Monthly":
            wallet.add_money(1000)

            await ctx.respond("Here are 1000 Coins.")
            return
        wallet.add_money(9999)
        await ctx.respond("Here is your Special!")

    @slash_command()
    async def buy(self, subject: Union[VoiceChannel, StageChannel, TextChannel, CategoryChannel, Role]):
        pass


def setup(bot: Bot):
    bot.add_cog(Currency(bot))
