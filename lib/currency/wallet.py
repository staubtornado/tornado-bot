from datetime import date

from discord import Member, Embed, User

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.utils.utils import shortened


class Wallet:
    def __init__(self, member: Member or User):
        self.user = member
        self.guild = self.user.guild

        self._cur = database.cursor()

        self._cur.execute("""SELECT Balance from wallets where UserID = ?""", (self.user.id, ))
        self.balance = self._cur.fetchone()
        if self.balance is None:
            self._cur.execute("""INSERT INTO wallets (UserID) VALUES (?)""", (self.user.id, ))
            self.balance = 0

        today = date.today().strftime("%d/%m/%Y")
        self._cur.execute("""SELECT LastModified from wallets where UserID = ?""", (self.user.id, ))
        if self._cur.fetchone() != today:
            self._cur.execute("""Update wallets SET LastModified = ? where UserID = ?""", (today, self.user.id))
            self._cur.execute("""Update wallets SET Revenue = 0 where UserID = ?""", (self.user.id, ))
            self.revenue = 0
        else:
            self._cur.execute("""SELECT Revenue from wallets where UserID = ?""", (self.user.id, ))
            self.revenue = self._cur.fetchone()

        self.is_bank = False

    def add_money(self, amount: int):
        self._cur.execute("""Update wallets SET Balance = Balance + ? where UserID = ?""", (amount, self.user.id))
        self.balance += amount
        self.revenue += amount

    def remove_money(self, amount: int):
        self._cur.execute("""Update wallets SET Balance = Balance - ? where UserID = ?""", (amount, self.user.id))
        self.balance -= amount

    def create_embed(self, estimated: bool = False) -> Embed:
        embed = Embed(title="Wallet", colour=SETTINGS["Colours"]["Default"])

        try:
            embed.set_author(name=self.user, icon_url=self.user.avatar.url)
        except AttributeError:
            embed.set_author(name=self.user, icon_url=self.user.default_avatar)

        if estimated:
            balance = shortened(self.balance, precision=0)
            revenue = shortened(self.revenue, precision=0)
        else:
            balance = self.balance
            revenue = self.revenue

        embed.add_field(name=f"{'Estimated ' if estimated else ''}Balance", value=balance)
        embed.add_field(name=f"Today's {'estimated ' if estimated else ''}Revenue", value=revenue)
        embed.set_footer(text="Re-execute command again to update information.")
        return embed
