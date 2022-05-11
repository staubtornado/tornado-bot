from math import ceil
from typing import Union

from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Role, \
    CategoryChannel, TextChannel, StageChannel, VoiceChannel, Guild, Embed
from discord.ext.commands import Cog
from discord.utils import basic_autocomplete

from data.config.settings import SETTINGS
from lib.currency.bank import Bank
from lib.currency.views import ConfirmTransaction
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

    @slash_command()
    async def transfer(self, ctx: ApplicationContext, amount: int, user: Member):
        """Sends an amount of coins from your wallet to a selected user."""
        await ctx.defer()

        bank = self.get_bank(ctx.guild)
        source = self.get_wallet(ctx.guild, ctx.author)
        destination = self.get_wallet(ctx.guild, user)

        amount_with_fee = amount + ceil(amount * (bank.fee + SETTINGS["Cogs"]["Economy"]["WallstreetFee"]))

        if source.balance - amount_with_fee < 0:
            await ctx.respond("❌ You do **not** have **enough coins**.")
            return
        if destination.is_bank:
            await ctx.respond(f"❌ {user} owns a server, meaning he owns his bank. Therefore, you cannot pay him.")
            return

        embed = Embed(title="Confirm", description=f"You are about to send {amount} coins to another user.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="Fee", value=bank.fee + SETTINGS["Cogs"]["Economy"]["WallstreetFee"])
        embed.add_field(name="Costs for you", value=amount_with_fee)
        embed.set_footer(text="You agree and understand, that this transaction is not reversible.")

        view = ConfirmTransaction()
        await ctx.respond(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            destination.balance -= amount_with_fee
            source.balance += amount
            source.revenue += amount
            bank.wallet.add_money(ceil(amount * bank.fee))
            self.wallstreet.wallet.add_money(ceil(amount * SETTINGS["Cogs"]["Economy"]["WallstreetFee"]))
            await ctx.respond(f"❌ **Transaction confirmed**: Transferred {amount} to {user.mention}.")
            return
        await ctx.respond("❌ **Transaction canceled**.", ephemeral=True)

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
