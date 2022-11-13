from typing import Union, Optional

from discord import Member


class ExperienceStats:
    xp: int
    total: Optional[int]
    level: int
    message_amount: Optional[int]
    member: Member

    def __init__(self, data: dict[str, Union[int, Member]]) -> None:
        self.xp = data.get("xp")
        self.total = data.get("total")
        self.level = data.get("level")
        self.message_amount = data.get("message_count")
        self.member = data.get("member")
