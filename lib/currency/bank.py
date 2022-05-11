from discord import Guild

from lib.currency.wallet import Wallet


class Bank:
    def __init__(self, guild: Guild):
        self.guild = guild

        self.wallets = {}
        self.fee = 0.05

        self.wallet = Wallet(guild.owner)
        self.wallet.is_bank = True
