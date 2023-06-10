from datetime import datetime
from os import environ
from typing import Optional, Any

from discord import Bot, Interaction, ApplicationContext, ApplicationCommandInvokeError

from config.settings import SETTINGS
from lib.logging import log, save_traceback
from lib.spotify.api import SpotifyAPI


class TornadoBot(Bot):
    uptime: datetime
    settings: dict[str, Any]
    spotify: SpotifyAPI

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._uptime = None
        self._settings = SETTINGS
        self._spotify = SpotifyAPI(environ["SPOTIFY_CLIENT_ID"], environ["SPOTIFY_CLIENT_SECRET"])

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

    async def on_ready(self) -> None:
        self._uptime = datetime.utcnow()
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
        await ctx.respond(f"❌ **Error** while **processing command**: `{exception.original.__class__.__name__}`")
        await save_traceback(exception)
