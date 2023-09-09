from dataclasses import dataclass, asdict

from lib.enums import SongEmbedSize


@dataclass
class Emoji:
    """
    Represents a custom emoji.

    :ivar emoji_id: The ID of the emoji.
    :ivar name: The name of the emoji.
    :ivar is_animated: Whether the emoji is animated.
    :ivar guild_id: The ID of the guild the emoji is from.
    """
    emoji_id: int
    name: str
    is_animated: bool
    guild_id: int

    def __str__(self) -> str:
        return f"<:{self.name}:{self.emoji_id}>" if not self.is_animated else f"<a:{self.name}:{self.emoji_id}>"

    def __bool__(self):
        return True

    def __iter__(self):
        yield from asdict(self).values()


@dataclass(slots=True)
class LevelingStats:
    """
    Represents the leveling stats of a user.

    :ivar guild_id: The ID of the guild the user is in.
    :ivar user_id: The ID of the user.
    :ivar experience: The experience of the user.
    :ivar message_count: The message count of the user.
    """
    guild_id: int
    user_id: int
    experience: int
    message_count: int

    def __bool__(self):
        return True

    def __iter__(self):
        yield from asdict(self).values()

    def __gt__(self, other):
        return self.experience > other.experience


@dataclass
class GuildSettings:
    """
    Represents the settings of a guild.

    :ivar guild_id: The ID of the guild.
    :ivar has_beta: Whether the guild has beta.
    :ivar has_premium: Whether the guild has premium.
    :ivar xp_active: Whether the leveling system is active.
    :ivar xp_multiplier: The multiplier of the leveling system.
    :ivar song_embed_size: The size of the song embed.
    :ivar log_channel_id: The ID of the log channel.
    :ivar send_welcome_message: Whether the welcome message should be sent.
    :ivar welcome_message: The welcome message.

    """

    guild_id: int
    has_beta: bool
    has_premium: bool

    xp_active: bool
    xp_multiplier: int

    song_embed_size: SongEmbedSize

    log_channel_id: int | None
    send_welcome_message: bool
    welcome_message: str

    def __bool__(self):
        return True

    def __iter__(self):
        yield from asdict(self).values()


@dataclass
class UserStats:
    """
    Represents the usage stats of a user.

    :ivar user_id: The ID of the user.
    :ivar commands_used: The number of commands used by the user.
    :ivar songs_played: The number of songs played by the user.
    :ivar songs_minutes: The number of minutes the user has listened to songs.
    """

    user_id: int
    commands_used: int
    songs_played: int
    songs_minutes: int

    def __bool__(self):
        return True

    def __iter__(self):
        yield from asdict(self).values()
