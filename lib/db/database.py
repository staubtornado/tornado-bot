from asyncio import AbstractEventLoop
from pathlib import Path

from aiosqlite import connect

from lib.db.emoji import Emoji


class Database:  # aiosqlite3
    def __init__(self, path: Path | str, loop: AbstractEventLoop) -> None:
        self._db = None
        loop.create_task(self._connect(path))

    async def _connect(self, path: Path | str) -> None:
        self._db = await connect(path)

    async def get_emoji(self, name: str) -> Emoji | None:
        """
        Gets an emoji from the database.
        :param name: The name of the emoji to get.
        :return: Emoji or None if not found.
        """

        async with self._db.execute("SELECT emoji, name, isAnimated, guildId FROM Emojis WHERE name = ?", (name,)) as cursor:
            if data := await cursor.fetchone():
                return Emoji(*data)

    async def set_emoji(self, emoji: Emoji) -> None:
        """
        Sets an emoji in the database.
        :param emoji: The emoji to set.
        :return: None

        :raises ValueError: If the guild is not an emoji guild.
        """

        async with self._db.execute(
            "SELECT guildId FROM EmojiGuilds WHERE guildId = ?;", (emoji.guild_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise ValueError(f"Guild {emoji.guild_id} is not in the system database.")

        async with self._db.execute(
                "REPLACE INTO Emojis (emoji, name, isAnimated, guildId) VALUES (?, ?, ?, ?);",
                (emoji.id, emoji.name, emoji.is_animated, emoji.guild_id)
        ):
            await self._db.commit()

    async def get_emoji_guilds(self) -> list[int]:
        """
        Gets all emoji guilds from the database.
        :return: List of guild IDs.
        """

        async with self._db.execute("SELECT guildId FROM EmojiGuilds;") as cursor:
            return [guild[0] for guild in await cursor.fetchall()]

    async def add_emoji_guild(self, guild_id: int) -> None:
        """
        Adds an emoji guild to the database.
        :param guild_id: The guild ID to add.
        :return: None
        """

        async with self._db.execute("INSERT INTO EmojiGuilds (guildId) VALUES (?);", (guild_id,)):
            await self._db.commit()


