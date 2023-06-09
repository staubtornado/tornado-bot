from os import environ, listdir

from discord import LoginFailure

from bot import TornadoBot
from lib.logging import log


def main() -> None:
    """Main entry point of the program."""

    # Load environment variables from .env file
    with open("./config/.env", "r") as file:
        for line in file.readlines():
            key, value = line.strip().split("=", 1)
            if key not in environ:
                environ[key] = value

    bot: TornadoBot = TornadoBot()

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
