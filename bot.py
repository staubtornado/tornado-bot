from datetime import datetime
from os import environ
from typing import Optional, Any

from discord import Bot, Interaction, ApplicationContext, ApplicationCommandInvokeError, Forbidden, HTTPException

from config.settings import SETTINGS
from lib.db.database import Database
from lib.db.db_classes import Emoji
from lib.emoji_loader import load_emojis
from lib.logging import log, save_traceback
from lib.spotify.api import SpotifyAPI
from lib.utils import random_hex


class TornadoBot(Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._uptime = None
        self._settings = SETTINGS
        self._spotify = SpotifyAPI(environ["SPOTIFY_CLIENT_ID"], environ["SPOTIFY_CLIENT_SECRET"])
        self._database = Database("./data/database.sqlite", self.loop)

    @property
    def uptime(self) -> Optional[datetime]:
        """Returns the time the bot was started. Might be None if the bot has not yet logged in."""
        return self._uptime

    @property
    def settings(self) -> dict[str, Any]:
        """Returns the settings dictionary."""
        return self._settings

    @property
    def spotify(self) -> SpotifyAPI:
        """Returns the Spotify API instance."""
        return self._spotify

    @property
    def database(self) -> Database:
        """Returns the database instance."""
        return self._database

    async def on_ready(self) -> None:
        self._uptime = datetime.utcnow()

        try:
            await load_emojis(self.database, self.guilds)
        except ValueError:
            log("No valid emoji guilds found. Creating new guild...")
            try:
                guild = await self.create_guild(name=random_hex(6))
            except (Forbidden, HTTPException):
                log("Failed to create new emoji guild", error=True)
            else:
                await self.database.add_emoji_guild(guild.id)
                log(f"Created new emoji guild {guild.name} ({guild.id})")
                await load_emojis(self.database, self.guilds)
        log(f"Logged in as {self.user.name} ({self.user.id})")

    async def on_interaction(self, interaction: Interaction) -> None:
        log(f"Received interaction {interaction.id} from {interaction.user.name} ({interaction.user.id})")
        await self.process_application_commands(interaction, auto_sync=None)

    async def on_application_command_error(
            self,
            ctx: ApplicationContext,
            exception: ApplicationCommandInvokeError
    ) -> None:
        log(f"Error while processing interaction {ctx.interaction.id}: {exception.original}", error=True)
        emoji_cross: Emoji = await self.database.get_emoji("cross")
        await ctx.respond(
            f"{emoji_cross} **Error** while **processing command**: `{exception.original.__class__.__name__}`"
        )
        await save_traceback(exception)
