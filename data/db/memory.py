from asyncio import sleep
from typing import Self

from aiosqlite import Connection, connect
from discord import Guild, Member

from data.config.settings import SETTINGS
from lib.db.data_objects import ExperienceStats, GuildSettings
from lib.experience.calculation import xp_to_level


class Database:
    _database: Connection
    _initialized: bool

    def __init__(self, con: Connection, loop) -> None:
        self._database = con
        self._initialized = False

        loop.create_task(self._sync_task())

    @classmethod
    async def create(cls, loop) -> Self:
        db = await connect(':memory:')
        return cls(db, loop)

    async def get_member_stats(self, member: Member) -> ExperienceStats:
        async with self._database.execute(
            """SELECT XP, Messages FROM experience WHERE GuildID = ? AND UserID = ?""",
            (member.guild.id, member.id,)
        ) as cur:
            result: tuple[int, int] = await cur.fetchone()

        if result is None:
            result = (0, 0)

        async with self._database.execute(
            """SELECT COUNT(*) FROM experience WHERE XP > ? AND GuildID = ? AND UserID != ?""",
            (result[0], member.guild.id, member.id)
        ) as cur2:
            rank: int = (await cur2.fetchone())[0] + 1

        return ExperienceStats({
            "xp": xp_to_level(result[0])[1],
            "total": result[0],
            "level": xp_to_level(result[0])[0],
            "member": member,
            "message_count": result[1],
            "rank": rank
        })

    async def update_leaderboard(self, stats: ExperienceStats) -> None:
        await self._database.execute(
            """INSERT OR IGNORE INTO experience (GuildID, UserID) VALUES (?, ?)""",
            (stats.member.guild.id, stats.member.id)
        )
        await self._database.execute(
            """UPDATE experience SET XP = ?, Messages = ? WHERE (GuildID, UserID) = (?, ?)""",
            (stats.total, stats.message_amount, stats.member.guild.id, stats.member.id)
        )
        await self._database.commit()

    async def get_leaderboard(self, guild: Guild) -> list[ExperienceStats]:
        async with self._database.execute(
            """SELECT XP, Messages, UserID FROM experience WHERE GuildID = ? ORDER BY XP DESC""",
            (guild.id,)
        ) as cur:
            rtrn: list[ExperienceStats] = []

            async for xp, messages, user_id in cur:
                if user := guild.get_member(user_id):
                    rtrn.append(ExperienceStats({
                        "xp": xp_to_level(xp)[1],
                        "total": xp,
                        "level": xp_to_level(xp)[0],
                        "member": user,
                        "message_count": messages
                    }))
                    continue

                await self._database.execute(
                    """DELETE FROM experience WHERE (GuildID, UserID) = (?, ?)""",
                    (guild.id, user_id)
                )
                await self._database.commit()
        return rtrn

    async def create_guild(self, guild: Guild) -> None:
        await self._database.execute(
            """INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""",
            (guild.id,)
        )
        await self._database.commit()

    async def remove_guild(self, guild: Guild) -> None:
        await self._database.execute(
            """DELETE FROM guilds WHERE GuildID = ?""",
            (guild.id,)
        )
        await self._database.execute(
            """DELETE FROM experience WHERE GuildID = ?""",
            (guild.id,)
        )
        await self._database.commit()

    async def remove_user(self, member: Member) -> None:
        await self._database.execute(
            """DELETE FROM experience WHERE (GuildID, UserID) = (?, ?)""",
            (member.guild.id, member.id)
        )
        await self._database.commit()

    async def get_guild_settings(self, guild: Guild) -> GuildSettings:
        await self._database.execute(
            """INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""",
            (guild.id,)
        )
        await self._database.commit()
        async with self._database.execute(
            """SELECT * FROM guilds WHERE GuildID = ?""",
            (guild.id,)
        ) as cur:
            return GuildSettings(guild, await cur.fetchone())

    async def update_guild_settings(self, settings: GuildSettings) -> None:
        await self._database.execute(
            """INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""",
            (settings.guild.id,)
        )
        await self._database.execute(
            """UPDATE guilds SET XPIsActivated = ?, XPMultiplier = ?, MusicEmbedSize = ?, RefreshMusicEmbed = ?, 
            GenerateAuditLog = ?, AuditLogChannel = ? WHERE GuildID = ?""",
            (
                settings.xp_is_activated,
                settings.xp_multiplier,
                settings.music_embed_size,
                settings.refresh_music_embed,
                settings.generate_audit_log,
                settings.audit_log_channel_id,
                settings.guild.id
            )
        )
        await self._database.commit()

    async def register_key(self, key: str, premium: bool, beta: bool) -> None:
        await self._database.execute(
            """INSERT OR IGNORE INTO keys (KeyString, EnablesPremium, EnablesBeta) VALUES (?, ?, ?)""",
            (key, premium, beta)
        )
        await self._database.commit()

    async def validate_key(self, key: str, premium: bool, beta: bool) -> None:
        async with self._database.execute(
            """SELECT * FROM keys WHERE KeyString = ?""",
            (key,)
        ) as cur:
            result: tuple[str, int, int] = await cur.fetchone()

        if result is None:
            raise KeyError("Key not found")

        if (premium, beta) != (bool(result[1]), bool(result[2])):
            raise KeyError("Key is not valid for this type of use")

        await self._database.execute(
            """DELETE FROM keys WHERE KeyString = ?""",
            (key,)
        )

    async def sync(self) -> None:
        async with connect('./data/db/database.db') as file_db:
            if not self._initialized:
                with open('./data/db/build.sql', 'r') as f:
                    await file_db.executescript(f.read())
                await file_db.commit()
                await file_db.backup(self._database)
                await self._database.commit()
                self._initialized = True
            else:
                await self._database.commit()
                await self._database.backup(file_db)
                await file_db.commit()

    async def _sync_task(self) -> None:
        while True:
            print()
            try:
                await self.sync()
            except Exception as e:
                print(e)
            await sleep(SETTINGS["ServiceSyncInSeconds"])
