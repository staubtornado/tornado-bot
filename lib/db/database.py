from asyncio import AbstractEventLoop
from pathlib import Path

from aiosqlite import connect

from lib.db.db_classes import Emoji, LevelingStats, GuildSettings, UserStats
from lib.enums import SongEmbedSize


def _open_file() -> bytes:
    with open("./lib/db/build.sql", "rb") as file:
        return file.read()


class Database:  # aiosqlite3
    def __init__(self, path: Path | str, loop: AbstractEventLoop) -> None:
        self._db = None
        self._loop = loop
        loop.create_task(self._connect(path))

    async def _connect(self, path: Path | str) -> None:
        # Check if database exists
        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            path.touch()
        self._db = await connect(path)

        #  Execute build.sql to create tables
        _bytes = await self._loop.run_in_executor(None, _open_file)
        await self._db.executescript(_bytes.decode("utf-8"))
        await self._db.commit()

    async def get_emoji(self, name: str) -> Emoji | None:
        """
        Gets an emoji from the database.
        :param name: The name of the emoji to get.
        :return: Emoji or None if not found.
        """

        async with self._db.execute(
                "SELECT emoji, name, isAnimated, guildId FROM Emojis WHERE name = ?", (name,)) as cursor:
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
                (emoji.emoji_id, emoji.name, emoji.is_animated, emoji.guild_id)
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

    async def get_guild_leaderboard(self, guild_id: int, limit: int = 19, offset: int = 0) -> list[LevelingStats]:
        """
        Gets the leaderboard for a guild.
        :param guild_id: The guild ID to get the leaderboard for.
        :param limit: The limit of users to get.
        :param offset: The offset to start from.
        :return: List of LevelingStats.
        """

        async with self._db.execute(
                "SELECT * FROM Leveling WHERE guildId = ? ORDER BY xp DESC LIMIT ?;",
                (guild_id, limit + offset)) as cursor:
            return [LevelingStats(*data) for data in await cursor.fetchall()][offset:]

    async def get_global_leaderboard(self, limit: int = 19, offset: int = 0) -> list[LevelingStats]:
        """
        Gets the global leaderboard.
        :param limit: The limit of users to get.
        :param offset: The offset to start from.
        :return: List of LevelingStats.
        """

        async with self._db.execute(
                "SELECT * FROM Leveling ORDER BY xp DESC LIMIT ?;",
                (limit + offset,)) as cursor:
            return [LevelingStats(*data) for data in await cursor.fetchall()]

    async def get_leveling_stats(self, user_id: int, guild_id: int) -> LevelingStats:
        """
        Gets a user's leveling stats.
        :param user_id: The user ID to get the stats for.
        :param guild_id: The guild ID to get the stats for.
        :return: LevelingStats
        """

        async with self._db.execute(
                "SELECT * FROM Leveling WHERE userId = ? AND guildId = ?;",
                (user_id, guild_id)) as cursor:
            if data := await cursor.fetchone():
                return LevelingStats(*data)
            return LevelingStats(guild_id, user_id, 0, 0)

    async def set_leveling_stats(self, stats: LevelingStats) -> None:
        """
        Sets a user's LevelingStats stats.
        :param stats: The stats to set.
        :return: None
        """

        async with self._db.execute("REPLACE INTO Leveling VALUES (?, ?, ?, ?);", (*stats,)):
            await self._db.commit()

    async def remove_leveling_stats(self, user_id: int | None, guild_id: int) -> None:
        """
        Removes a user's LevelingStats stats.
        :param user_id: The user ID to remove the stats for.
        :param guild_id: The guild ID to remove the stats for.
        :return: None
        """

        if not user_id:
            async with self._db.execute("DELETE FROM Leveling WHERE guildId = ?;", (guild_id,)):
                await self._db.commit()
            return

        async with self._db.execute("DELETE FROM Leveling WHERE userId = ? AND guildId = ?;", (user_id, guild_id)):
            await self._db.commit()

    async def get_guild_settings(self, guild_id: int) -> GuildSettings:
        """
        Gets a guild's settings.
        :param guild_id: The guild ID to get the settings for.
        :return: GuildSettings.
        """

        async with self._db.execute("SELECT * FROM GuildSettings WHERE guildId = ?;", (guild_id,)) as cursor:
            if data := await cursor.fetchone():
                return GuildSettings(*data)
            return GuildSettings(
                guild_id,  # guildId
                False,  # beta
                False,  # premium
                True,  # leveling
                1,  # levelingMultiplier
                SongEmbedSize.DEFAULT,  # songEmbedSize
                None,  # logChannelId
                False,  # welcome
                "Welcome {user} to {guild}!"  # welcomeMessage
            )

    async def set_guild_settings(self, settings: GuildSettings) -> None:
        """
        Sets a guild's settings.
        :param settings: The settings to set.
        :return: None
        """

        async with self._db.execute("REPLACE INTO GuildSettings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", (*settings,)):
            await self._db.commit()

    async def remove_guild_settings(self, guild_id: int) -> None:
        """
        Removes the guild's settings.
        :param guild_id: The guild ID to remove the settings for.
        :return: None
        """

        async with self._db.execute("DELETE FROM GuildSettings WHERE guildId = ?;", (guild_id,)):
            await self._db.commit()

    async def get_user_stats(self, user_id: int) -> UserStats:
        """
        Gets a user's leveling stats.
        :param user_id: The user ID to get the stats for.
        :return: UserStats
        """

        async with self._db.execute(
                "SELECT * FROM UserStats WHERE userId = ?;", (user_id,)) as cursor:
            if data := await cursor.fetchone():
                return UserStats(*data)
            return UserStats(user_id, 0, 0, 0)

    async def set_user_stats(self, stats: UserStats | None) -> None:
        """
        Sets a user's UserStats stats.
        :param stats: The stats to set.
        :return: None
        """

        if not stats:
            async with self._db.execute("DELETE FROM UserStats WHERE userId = ?;", (stats.user_id,)):
                await self._db.commit()
            return

        async with self._db.execute("REPLACE INTO UserStats VALUES (?, ?, ?, ?);", (*stats,)):
            await self._db.commit()
