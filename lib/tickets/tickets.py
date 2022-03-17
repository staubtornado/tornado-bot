from sqlite3 import Cursor

from discord import Interaction

from data.db.memory import database


class TicketSystem:
    def __init__(self, ctx: Interaction):
        self.ctx = ctx

        cur: Cursor = database.cursor()

        query: str = """SELECT """

    async def create(self):
        pass

    async def delete(self):
        pass

    async def transcript(self):
        pass

    async def open(self):
        pass

    async def close(self):
        pass

    async def confirm(self):
        pass
