from dataclasses import dataclass, asdict


@dataclass
class Emoji:
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
