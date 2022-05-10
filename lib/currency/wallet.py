from discord import Member, Guild, Embed

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.utils.utils import shortened


class Wallet:
    def __init__(self, member: Member, target: Member = None):
        self.user = target or member
        self.guild = self.user.guild

        self._estimated = target is not None
        self._cur = database.cursor()

    def create_embed(self) -> Embed:
        get_balance = """SELECT Balance from wallets where UserID = ?"""
        get_revenue = """SELECT Revenue from wallets where UserID = ?"""
        get_timestamp = """SELECT LastModified from wallets where UserID = ?"""

        self._cur.execute(get_balance, self.user.id)
        balance = self._cur.fetchone()

        self._cur.execute(get_revenue, self.user.id)
        revenue = self._cur.fetchone()
        self._cur.execute(get_timestamp, self.user.id)
        if self._cur.fetchone() != "today":  # TODO: ADD CHECK
            revenue = 0

        if self._estimated:
            balance = shortened(balance, precision=0)
            revenue = shortened(revenue, precision=0)

        embed = Embed(title="Wallet", colour=SETTINGS["Colours"]["Default"])

        try:
            embed.set_author(name=self.user, icon_url=self.user.avatar.url)
        except AttributeError:
            embed.set_author(name=self.user, icon_url=self.user.default_avatar)

        embed.add_field(name=f"{'Estimated ' if self._estimated else ''}Balance", value=balance)
        embed.add_field(name=f"{'Estimated ' if self._estimated else ''}Revenue", value=revenue)

        embed.set_footer(text="Re-execute command again to update information.")
        return embed


class GuildBank:
    def __init__(self, guild: Guild):
        self.guild = guild


class GlobalBank:
    pass
