from discord import Bot

from data.config.settings import SETTINGS
from lib.currency.wallet import Wallet


class Wallstreet:
    def __init__(self, bot: Bot):
        self.wallet = Wallet(bot.get_user(SETTINGS["OwnerIDs"][0]))
