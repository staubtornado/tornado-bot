from datetime import date
from math import ceil
from random import choice
from re import findall
from sqlite3 import IntegrityError
from typing import Union

from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Embed, User
from discord.ext.commands import Cog
from discord.utils import basic_autocomplete

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.currency.views import ConfirmTransaction
from lib.currency.wallet import Wallet


# Concept:
# Every user has a global _balance and a tab that shows the revenue on the current server
# They can buy roles, channels, messages, advertisement, users aso with their global _balance on every server
# Every transaction gives a small percentage to the global bank and to the guild-bank for the specific server
# User can claim their money by executing a command every day /claim [daily | monthly | special] for example
# Users are limited to a specific amount of transactions per server every day and have a daily global limit
# Every stat is public, but only the user themselves can see their accurate stats. Others only see estimations
# Every bot has it own economy, meaning that self-hosted versions cannot access the official economy
# Users can invest their _balance: Daily revenue is linear and investments can be percentage increases


def get_claim_options(ctx: AutocompleteContext) -> list:
    return [choice(["Daily", "Monthly", "Special"])]


def get_property(ctx: Union[AutocompleteContext, ApplicationContext]) -> list:
    rtrn = []
    for role in ctx.interaction.guild.roles:
        if "(property-owner)" in role.name:
            if str(ctx.interaction.user.id) in role.name:
                subject = ctx.bot.get_channel(list(map(int, findall(r'\d+', role.name)))[1])
                rtrn.append(f"{subject.name} ({subject.id})") if subject is not None else None
    return rtrn


def get_server_subjects(ctx: Union[AutocompleteContext, ApplicationContext]) -> list:
    cur = database.cursor()
    cur.execute("""SELECT Subject, Price FROM subjects WHERE GuildID = ?""", (ctx.interaction.guild.id,))

    subjects = cur.fetchall()
    rtrn = []
    if subjects is not None:
        for subject in subjects:
            channel = ctx.bot.get_channel(subject[0])
            rtrn.append(f"{channel.name} ({channel.id}) for {subject[1]}")
    return rtrn


class Currency(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.wallets = {}

    def _transfer(self, ctx: ApplicationContext, amount: int, source: Wallet, destination: Wallet,
                  transaction: tuple = None):
        if not bool(transaction):
            try:
                self.wallets[ctx.guild.owner_id]
            except KeyError:
                self.wallets[ctx.guild.owner_id] = Wallet(ctx.guild.owner)
            local_fee: float = self.wallets[ctx.guild.owner_id].fee
            global_fee: float = SETTINGS["Cogs"]["Economy"]["WallstreetFee"]
            costs = amount + ceil(amount * (local_fee + global_fee))

            if source.get_balance() - costs < 0 or amount < 0:
                return "❌ You do **not** have **enough coins**."
            if destination.fee != 0 and not transaction:
                return f"❌ {destination.user} makes **money through fees** on this server: You **cannot pay him**."
            return costs, local_fee, global_fee

        costs, local_fee, global_fee = transaction

        source.set_balance(source.get_balance() - costs)
        destination.set_balance(destination.get_balance() + amount)
        self.wallets[ctx.guild.owner_id].set_balance(self.wallets[ctx.guild.owner_id].get_balance() +
                                                     ceil(amount * local_fee))
        self.wallets[SETTINGS["OwnerIDs"][0]].set_balance(self.wallets[ctx.guild.owner_id].get_balance() +
                                                          ceil(amount *
                                                               SETTINGS["Cogs"]["Economy"]["WallstreetFee"]))
        return f":white_check_mark: **Transaction confirmed**: Transferred {amount} to {destination.user.mention}."

    def save_get_wallet(self, member: Union[Member, User]) -> Wallet:
        try:
            self.wallets[member.id]
        except KeyError:
            self.wallets[member.id] = Wallet(member)
        return self.wallets[member.id]

    async def cog_before_invoke(self, ctx: ApplicationContext):
        try:
            self.wallets[SETTINGS["OwnerIDs"][0]]
        except KeyError:
            self.wallets[SETTINGS["OwnerIDs"][0]] = Wallet(self.bot.get_user(SETTINGS["OwnerIDs"][0]))

        try:
            self.wallets[ctx.author.id]
        except KeyError:
            self.wallets[ctx.author.id] = Wallet(ctx.author)

    @slash_command()
    async def wallet(self, ctx: ApplicationContext, *, user: Member = None):
        """Displays information about your wallet."""
        await ctx.defer()
        target = user or ctx.author

        try:
            self.wallets[target.id]
        except KeyError:
            await ctx.respond("❌ This **user** is currently **not active**.")
            return

        wallet: Wallet = self.wallets[target.id]
        await ctx.respond(embed=wallet.create_embed(estimated=bool(user)))

    @slash_command()
    async def transfer(self, ctx: ApplicationContext, amount: int, user: Member):
        """Sends an amount of coins from your wallet to a selected user."""
        await ctx.defer(ephemeral=True)

        source: Wallet = self.wallets[ctx.author.id]
        try:
            self.wallets[user.id]
        except KeyError:
            await ctx.respond("❌ This **user** is currently **not active**.")
            return
        destination: Wallet = self.wallets[user.id]

        transaction = self._transfer(ctx, amount, source, destination)
        if isinstance(transaction, str):
            await ctx.respond(transaction)
            return
        costs, local_fee, global_fee = transaction

        embed = Embed(title="Confirm", description=f"You are about to send {amount} coins to another user.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="Fee", value=f"{(local_fee + global_fee) * 100}%")
        embed.add_field(name="Costs for you", value=costs)
        embed.set_footer(text="You agree and understand, that this transaction is not reversible.")

        view = ConfirmTransaction()
        await ctx.respond(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            await ctx.respond(self._transfer(ctx, amount, source, destination, transaction=transaction))
            return
        await ctx.respond("❌ **Transaction canceled**.", ephemeral=True)

    @slash_command()
    async def claim(self, ctx: ApplicationContext,
                    offer: Option(str, "Choose what you want to claim. Options might vary.",
                                  autocomplete=basic_autocomplete(get_claim_options), required=True)):
        """Claim your current offers."""
        await ctx.defer()
        wallet = self.wallets[ctx.author.id]

        if offer == "Daily":
            wallet.set_balance(wallet.get_balance() + 100)

            await ctx.respond("👉 Here are your daily **one hundred Coins on this server**.")
            return
        if offer == "Monthly":
            wallet.set_balance(wallet.get_balance() + 1000)

            await ctx.respond("👉 Here is your monthly reward, one thousand coins, on this server.")
            return
        wallet.set_balance(wallet.get_balance() + 9999)
        await ctx.respond("Here is your Special!")

    @slash_command()
    async def sell(self, ctx: ApplicationContext,
                   subject: Option(str, "The subject you want to sell. If nothing appears, nothing is available.",
                                   autocomplete=get_property, required=True), price: int):
        """Sell something you own on this server. You receive the money once a user buys it."""

        integers_in_subject = list(map(int, findall(r'\d+', subject)))
        subject = ctx.bot.get_channel(integers_in_subject[len(integers_in_subject) - 1])
        embed = Embed(title="Confirm", description=f"You are about to sell {subject.mention} for {price}.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.set_footer(text="I understand that my transaction may be canceled by a server admin or bot admin, and I "
                              "may lose the subject I am selling. This cannot be reverted.")

        view = ConfirmTransaction()
        await ctx.respond(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            try:

                cur = database.cursor()
                cur.execute("""INSERT INTO subjects (GuildID, Subject, Seller, Price, Added) VALUES (?, ?, ?, ?, ?)""",
                            (ctx.guild.id, subject.id, ctx.author.id, price, date.today().strftime("%d/%m/%Y")))
            except IntegrityError:
                await ctx.respond("❌ You **cannot sell this property** anymore.", ephemeral=True)
                return
            await ctx.respond(f":white_check_mark: Successfully **sold** {subject.mention} **for {price}**.")
            return
        await ctx.respond("❌ **Successfully canceled**.", ephemeral=True)

    @slash_command()
    async def buy(self, ctx: ApplicationContext,
                  subject: Option(str, "The subject you want to buy. If nothing appears, nothing is available.",
                                  autocomplete=get_server_subjects, required=True)):
        """Buy subjects on this server. Users need to /sell something before you can buy it."""
        await ctx.defer(ephemeral=True)

        if subject not in get_server_subjects(ctx):
            await ctx.respond(f"❌ {subject} is **not for sale**.")
            return

        price = int(subject.split(" for ")[1])
        subject = self.bot.get_channel(int(subject.split("(")[1][0:18]))
        cur = database.cursor()

        cur.execute("""SELECT Seller FROM subjects WHERE (GuildID, Subject) = (?, ?)""", (ctx.guild.id, subject.id))

        try:
            user = self.bot.get_user(cur.fetchone()[0])
            if user is None:
                raise IndexError
            destination = self.save_get_wallet(user)
        except IndexError:
            cur.execute("""DELETE FROM subjects WHERE (GuildID, Subject) = (?, ?)""", (ctx.guild.id, subject.id))
            await ctx.respond(f"❌ {subject.mention} **cannot be bought**.")
            return

        transaction = self._transfer(ctx, price, self.wallets[ctx.author.id], destination)
        if isinstance(transaction, str):
            await ctx.respond(transaction)
            return
        costs, local_fee, global_fee = transaction

        embed = Embed(title="Confirm", description=f"You are about to buy **{subject.mention}** for **{price}**.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="Fee", value=f"{(local_fee + global_fee) * 100}%")
        embed.add_field(name="Total costs", value=costs)
        embed.set_footer(text="I understand that I only receive the permission to use the subject and that I do not "
                              "own it. I may loose it due to server or bot admins.")

        view = ConfirmTransaction()
        await ctx.respond(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            await ctx.respond(self._transfer(ctx, price, self.wallets[ctx.author.id], destination,
                                             transaction=transaction))

            cur = database.cursor()
            cur.execute("""DELETE FROM subjects WHERE (GuildID, Subject) = (?, ?)""", (ctx.guild.id, subject.id))
            await ctx.respond(f":white_check_mark: Successfully **bought** {subject.mention} **for {price}**.")
            return
        await ctx.respond("❌ **Successfully canceled**.", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Currency(bot))
