from datetime import date
from typing import Union

from discord import Member, Embed, User

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.utils.utils import shortened


class Wallet:
    def __init__(self, member: Union[Member, User]):
        self.user = member

        self._cur = database.cursor()
        self._revenue = None

        self._cur.execute("""SELECT Fee from wallets where UserID = ?""", (self.user.id, ))
        try:
            self.fee = self._cur.fetchone()[0]
        except TypeError:
            self.fee = 0

        self._cur.execute("""SELECT Balance from wallets where UserID = ?""", (self.user.id, ))
        self._balance = self._cur.fetchone()

        try:
            self._balance = self._balance[0]
        except TypeError:
            self._cur.execute("""INSERT INTO wallets (UserID) VALUES (?)""", (self.user.id, ))
            self._balance = 0
        print(member)

        self._check_revenue()
        if self._revenue != 0:
            self._cur.execute("""SELECT Revenue from wallets where UserID = ?""", (self.user.id, ))
            self._revenue = self._cur.fetchone()[0]

    def _check_revenue(self):
        today = date.today().strftime("%d/%m/%Y")
        self._cur.execute("""SELECT LastModified from wallets where UserID = ?""", (self.user.id, ))
        if self._cur.fetchone()[0] != today:

            self._cur.execute("""Update wallets SET LastModified = ? where UserID = ?""", (today, self.user.id))
            self._cur.execute("""Update wallets SET Revenue = 0 where UserID = ?""", (self.user.id, ))
            self._revenue = 0

    def get_balance(self) -> int:
        return self._balance

    def set_balance(self, amount: int):
        if amount > self._balance:
            self._revenue += amount - self._balance
            self._cur.execute("""Update wallets SET Revenue = ? where UserID = ?""", (self._revenue, self.user.id))
        self._balance = amount
        self._cur.execute("""Update wallets SET Balance = ? where UserID = ?""", (self._balance, self.user.id))

    def create_embed(self, estimated: bool = False) -> Embed:
        embed = Embed(title="Wallet", colour=SETTINGS["Colours"]["Default"])

        try:
            embed.set_author(name=self.user, icon_url=self.user.avatar.url)
        except AttributeError:
            embed.set_author(name=self.user, icon_url=self.user.default_avatar)

        if estimated:
            balance = shortened(self._balance, precision=0)
            revenue = shortened(self._revenue, precision=0)
        else:
            balance = self._balance
            revenue = self._revenue

        embed.add_field(name=f"{'Estimated ' if estimated else ''}Balance", value=balance)
        embed.add_field(name=f"Today's {'estimated ' if estimated else ''}Revenue", value=revenue)
        embed.set_footer(text=f"Re-execute command again to update information.")
        return embed
