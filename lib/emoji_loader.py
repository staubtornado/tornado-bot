from asyncio import get_event_loop
from os import listdir

from discord import Guild, Forbidden, HTTPException

from lib.logging import log


def _open_file(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


async def load_emojis(guild: Guild) -> None:
    """
    Loads all emojis from ./assets/emojis to the given guild.
    :param guild: The guild to load the emojis to.

    :return: None
    """

    loop = get_event_loop()

    # List all files under ./assets/emojis
    for emoji in listdir("./assets/emojis"):

        # If the file is a PNG and not an emoji, load it
        if emoji.endswith(".png"):
            if emoji[:-4] in [e.name for e in guild.emojis]:
                continue

            #  Load the file in a separate thread
            _bytes = await loop.run_in_executor(None, _open_file, f"./assets/emojis/{emoji}")

            try:
                await guild.create_custom_emoji(name=emoji[:-4], image=_bytes)
            except (Forbidden, HTTPException):
                log(f"Failed to load emoji {emoji[:-4]} to guild {guild.name} ({guild.id})", error=True)
                break
            log(f"Loaded emoji {emoji[:-4]} to guild {guild.name} ({guild.id})")
