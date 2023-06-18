from dataclasses import dataclass


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
