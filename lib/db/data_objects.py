from enum import IntEnum
from typing import Optional, Union

from discord import Member, Guild


class EmbedSize(IntEnum):
    SMALL = 0  # Only contains description with source, duration Aso...
    NO_QUEUE = 1  # Everything except the queue
    DEFAULT = 2  # Dynamic queue, contains all essential information


class AutoModLevel(IntEnum):
    NONE = 0
    MEDIUM = 1


class GuildSettings:
    guild: Guild

    has_beta_features: bool
    has_premium: bool

    xp_is_activated: bool
    xp_multiplier: int

    music_embed_size: EmbedSize
    refresh_music_embed: bool

    generate_audit_log: bool
    audit_log_channel_id: Optional[int]
    welcome_message: bool

    auto_mod_level: AutoModLevel

    def __init__(self, guild: Guild, data: tuple[Optional[int]]):
        self.guild = guild

        self.has_beta_features = bool(data[1])
        self.has_premium = bool(data[2])
        self.xp_is_activated = bool(data[3])
        self.xp_multiplier = data[4]
        self.music_embed_size = EmbedSize(data[5])
        self.refresh_music_embed = bool(data[6])
        self.generate_audit_log = bool(data[7])
        self.audit_log_channel_id = data[8]
        self.welcome_message = bool(data[9])
        self.auto_mod_level = AutoModLevel(data[10])


class ExperienceStats:
    member: Member
    xp: int
    total: int
    level: int
    message_amount: int
    rank: Optional[int]

    def __init__(self, data: dict[str, Union[int, Member]]) -> None:
        self.xp = data.get("xp")
        self.total = data.get("total")
        self.level = data.get("level")
        self.message_amount = data.get("message_count")
        self.member = data.get("member")
        self.rank = data.get("rank")
