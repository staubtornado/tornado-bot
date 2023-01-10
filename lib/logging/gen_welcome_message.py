from io import BytesIO
from typing import Optional

from PIL import Image
from discord import Member, File, Asset
from easy_pil import Editor, Font
from numpy import average

from lib.utils.utils import read_file, ordinal


async def generate_welcome_message(member: Member, banner: Optional[Asset]) -> File:
    _banner: Optional[bytes] = None
    if banner is not None:
        _banner = await banner.read()
    try:
        _avatar: bytes = await member.avatar.read()
    except AttributeError:
        _avatar: bytes = await member.default_avatar.read()
    avatar: Editor = Editor(BytesIO(_avatar)).circle_image().resize(size=(200, 200))
    color: tuple[int, int, int, int] = tuple(
        average(avatar.image, axis=(0, 1)).astype(int)
    )

    # https://stackoverflow.com/a/3943023
    white_mode: bool = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114 > 186
    modes: dict[bool, str] = {True: "white", False: "black"}

    banner: Editor = Editor(Image.new("RGBA", (1100, 500), color=(*color[:3], 255)))
    banner.paste(
        Editor(BytesIO(_banner or _avatar)).resize(size=(1100, 200), crop=True).blur(
            amount=3 if _banner is not None else 80
        ), (0, 300)
    )
    banner.paste(
        Editor(BytesIO(await read_file(f"./assets/welcome_message_{modes[not white_mode]}.png"))),
        (0, 0)
    )
    del color, _avatar, _banner

    banner.text(
        position=(550, 240),
        text=str(member),
        align="center",
        color=modes[white_mode],
        font=Font(path="./assets/font.ttf", size=35)
    )
    banner.text(
        position=(550, 290),
        text=f"{ordinal(member.guild.member_count)} Member",
        align="center",
        color=modes[white_mode],
        font=Font(path="./assets/font.ttf", size=27)
    )
    banner.text(
        position=(550, 320),
        text=f"On Discord since {member.created_at.strftime('%B %Y')}",
        align="center",
        color=modes[white_mode],
        font=Font(path="./assets/font.ttf", size=27)
    )
    banner.paste(avatar, (450, 25))
    return File(banner.image_bytes, filename="welcome_message.png")
