from asyncio import get_event_loop, sleep
from os import listdir

from discord import Guild, Forbidden, HTTPException

from lib.db.database import Database
from lib.db.emoji import Emoji
from lib.logging import log


def _open_file(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


async def load_emojis(database: Database, _guilds: list[Guild]) -> None:
    """
    Loads all emojis from ./assets/emojis to the database.
    :param database: Database
    :param _guilds: All guilds the bot is in.

    :return: None

    :raises ValueError: If no valid emoji guilds are found.
    """

    loop = get_event_loop()
    emoji_guilds = await database.get_emoji_guilds()

    # Filter out guilds
    guilds: list[Guild] = []
    for guild in _guilds:
        if guild.id in emoji_guilds and len(guild.emojis) < 50:
            guilds.append(guild)
        await sleep(0)  # Prevent blocking
    del _guilds
    del emoji_guilds

    if not guilds:
        raise ValueError("No valid emoji guilds found.")

    # List all files under ./assets/emojis
    for emoji in listdir("./assets/emojis"):

        # If the file is a PNG and not an emoji, load it
        if emoji.endswith(".png"):

            # If the emoji is already in the database, skip it
            if _emoji := await database.get_emoji(emoji[:-4]):
                if _emoji.guild_id in [guild.id for guild in guilds]:
                    continue

            #  Load the file in a separate thread
            _bytes = await loop.run_in_executor(None, _open_file, f"./assets/emojis/{emoji}")

            try:
                _emoji = await guilds[0].create_custom_emoji(name=emoji[:-4], image=_bytes)
            except (Forbidden, HTTPException):
                log(f"Failed to load emoji {emoji[:-4]} to guild {guilds[0].name} ({guilds[0].id})", error=True)
                break

            await database.set_emoji(Emoji(_emoji.id, _emoji.name, _emoji.animated, guilds[0].id))
            log(f"Loaded emoji {emoji[:-4]} to guild {guilds[0].name} ({guilds[0].id})")
