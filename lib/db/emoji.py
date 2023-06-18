from typing import Self


class Emoji:
    def __init__(self, emoji_id: int, name: str, is_animated: bool, guild_id: int) -> None:
        self._id = emoji_id
        self._name = name
        self._is_animated = is_animated
        self._guild_id = guild_id

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_animated(self) -> bool:
        return self._is_animated

    @property
    def guild_id(self) -> int:
        return self._guild_id

    def __repr__(self) -> str:
        return f"<Emoji id={self.id} name={self.name} guild_id={self.guild_id}>"

    def __str__(self) -> str:
        return f"<:{self.name}:{self.id}>" if not self.is_animated else f"<a:{self.name}:{self.id}>"

    def __eq__(self, other: Self) -> bool:
        return self.id == other.id

    def __bool__(self):
        return True
