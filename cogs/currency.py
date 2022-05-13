from math import ceil

from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Embed
from discord.ext.commands import Cog
from discord.utils import basic_autocomplete

from data.config.settings import SETTINGS
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
    return ["Daily", "Monthly", "Special"]


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
                self.wallets[ctx.guild.owner_id] = Wallet(ctx.guild.owner_id)
            local_fee: float = self.wallets[ctx.guild.owner_id].fee
            global_fee: float = SETTINGS["Cogs"]["Economy"]["WallstreetFee"]
            costs = amount + ceil(amount * (local_fee + global_fee))

            if source.get_balance() - costs < 0:
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

    def get_wallet(self, member: Member) -> Wallet:
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
        embed.add_field(name="Fee", value=f"{local_fee + global_fee}%")
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
        wallet = self.get_wallet(ctx.author)

        if offer == "Daily":
            wallet.set_balance(wallet.get_balance() + 100)

            await ctx.respond("Here are 100 Coins.")
            return
        if offer == "Monthly":
            wallet.set_balance(wallet.get_balance() + 1000)

            await ctx.respond("Here are 1000 Coins.")
            return
        wallet.set_balance(wallet.get_balance() + 9999)
        await ctx.respond("Here is your Special!")

    @slash_command()
    async def sell(self, ctx: ApplicationContext, subject: Union[VoiceChannel, TextChannel], price: int):
        embed = Embed(title="Confirm", description=f"You are about to sell {subject.mention} for {price}.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.set_footer(text="I understand that my transaction may be canceled by a server admin or bot admin, and I "
                              "may lose the subject I am selling. This cannot be reverted.")

        view = ConfirmTransaction()
        await ctx.respond(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            cur = database.cursor()
            cur.execute("""INSERT INTO subjects (GuildID, Subject, Seller, Price, Added) VALUES (?, ?, ?, ?, ?)""",
                        (ctx.guild.id, subject.id, ctx.author.id, price, date.today().strftime("%d/%m/%Y")))
            await ctx.respond(f":white_check_mark: Successfully **sold** {subject.mention} **for {price}**.")
            return
        await ctx.respond("❌ **Successfully canceled**.", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Currency(bot))
