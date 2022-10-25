from discord import Interaction


class TicketSystem:
    def __init__(self, ctx: Interaction):
        self._ctx = ctx

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
