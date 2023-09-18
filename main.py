from os import environ, listdir

from discord import LoginFailure

from bot import TornadoBot
from config.settings import SETTINGS
from lib.logging import log


def main() -> None:
    """Main entry point of the program."""

    # Load environment variables from .env file
    try:
        with open("./config/.env", "r") as file:
            for line in file.readlines():
                key, value = line.strip().split("=", 1)
                key, value = key.strip(), value.strip()

                if key not in environ:
                    environ[key] = value
    except FileNotFoundError:
        log("No .env file found. Create on in the config folder.", error=True)
        return

    # Check if all environment variables are present
    if not all(key in environ for key in ["DISCORD_TOKEN", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]):
        log("Not all environment variables found. Check your .env file.", error=True)
        return
    bot: TornadoBot = TornadoBot(
        owner_ids=SETTINGS["OwnerIDs"],
        description=SETTINGS["Description"],
        intents=SETTINGS["Intents"],
    )

    # Load cogs
    for cog in listdir('./cogs'):
        if cog.endswith('.py') and not cog.startswith('_'):
            bot.load_extension(f'cogs.{cog[:-3]}')

    try:
        bot.run(environ["DISCORD_TOKEN"])
    except LoginFailure:
        log("Failed to log in to Discord. Check your token.", error=True)


if __name__ == "__main__":
    main()
