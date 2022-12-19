from abc import ABC
from logging import getLogger, FileHandler, Formatter, DEBUG
from time import time, strftime, localtime

from discord import Bot, Interaction, ApplicationContext, CheckFailure, ApplicationCommandInvokeError

from data.config.settings import SETTINGS
from data.db.memory import Database
from lib.utils.utils import save_traceback


class CustomBot(Bot, ABC):
    database: Database
    uptime: int
    latencies: list[int]  # milliseconds

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.database = self.loop.run_until_complete(Database.create(self.loop))
        self.latencies = []

        logger = getLogger('discord')
        logger.setLevel(DEBUG)
        handler = FileHandler(filename='discord.log', encoding='utf-8', mode='w')
        handler.setFormatter(Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        logger.addHandler(handler)

    async def on_ready(self) -> None:
        self.uptime = round(time())
        self.latencies.clear()
        print(f"[SYSTEM] {self.user} is online...")

    async def on_interaction(self, interaction: Interaction):
        await self.process_application_commands(interaction, auto_sync=None)

        if interaction.is_command():
            print(f"[DEFAULT] [{strftime('%d.%m.%y %H:%M', localtime())}] "
                  f"{interaction.user} executed /{interaction.data['name']} in {interaction.guild}")

    async def on_application_command_error(self, ctx: ApplicationContext, error):
        if not SETTINGS["Production"]:
            await ctx.respond(f"❌ An **error occurred**: `{error}`.")
            raise error
        save_traceback(error)
        print(
            f"[ERROR] [{strftime('%d.%m.%y %H:%M', localtime())}] {ctx.user} executed {ctx.command.name} in {ctx.guild}"
        )

        if isinstance(error, CheckFailure):
            if ctx.command.name == "play":
                await ctx.respond("❌ This **command** is **restricted to beta** guilds.\n"
                                  "👉 Use **/**`settings beta` to **enter the closed beta**.")
                return
            await ctx.respond("❌ This guild is **not permitted to use** that **command**.")
            return

        if isinstance(error, ApplicationCommandInvokeError):
            await ctx.respond(f"❌ An **error occurred**: `{error}`.")
            return
        raise error
