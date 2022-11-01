from typing import Any, Union

from discord import Member, TextChannel, Embed, ApplicationContext, Bot
from discord.ui import View


class Game:
    players: list[Member, Any]  # Will always be type Member
    bot: Bot
    _channel: Union[TextChannel, Any]  # Will always be type TextChannel

    def __init__(self, ctx: ApplicationContext, players: list[Member]):
        self.players = players
        self.bot = ctx.bot
        self._channel = ctx.channel

    async def send(self, msg: str = None, embed: Embed = None, view: View = None, delete_after: float = None) -> None:
        if msg is None and embed is None:
            raise ValueError("Cannot send an empty message.")
        await self._channel.send(content=msg, embed=embed, view=view, delete_after=delete_after)


class TicTacToe(Game):
    pass
