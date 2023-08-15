from asyncio import AbstractEventLoop, get_event_loop
from datetime import datetime
from io import BytesIO

from PIL import Image
from discord import Member, File
from easy_pil import Editor, Font
from numpy import average

from lib.utils import ordinal


def _generate_welcome_message(
        member_uname: str,
        created_at: datetime,
        banner: bytes | None,
        avatar: bytes,
        member_count: int,
) -> File:
    """
    Generates a welcome message for the given member.

    :param member_uname: The member's username.
    :param created_at: The member's creation date.
    :param banner: The banner to use.
    :param avatar: The avatar to use.
    :param member_count: The member count of the guild.

    :return: The welcome message as a :class:`discord.File`.
    """

    _avatar: Editor = Editor(BytesIO(avatar)).circle_image().resize(size=(200, 200))
    color: tuple[int, int, int, int] = tuple(
        average(_avatar.image, axis=(0, 1)).astype(int)
    )

    _banner: Editor = Editor(Image.new("RGBA", (1100, 500), color=(color[0], color[1], color[2], 255)))
    _banner.paste(  # Paste the banner or the blurred avatar.
        Editor(BytesIO(banner or avatar)).resize(size=(1100, 200), crop=True).blur(
            amount=3 if banner is not None else 80
        ), (0, 300)
    )
    _banner.paste(Editor(f"./assets/welcome_message.png"), (0, 0))  # Paste the base image.

    # Paste the avatar.
    _banner.paste(_avatar, (450, 25))
    del _avatar

    # Paste the username.
    _banner.text(
        text=member_uname,
        position=(550, 240),
        font=Font("./assets/fonts/Roboto/Roboto-Regular.ttf", 35),
        color=(255, 255, 255),
        align="center"
    )

    _banner.text(
        position=(550, 290),
        text=f"{ordinal(member_count)} Member",
        align="center",
        color=(255, 255, 255),
        font=Font(path="./assets/fonts/Roboto/Roboto-Regular.ttf", size=27)
    )
    _banner.text(
        position=(550, 320),
        text=f"On Discord since {created_at.strftime('%B %Y')}",
        align="center",
        color=(255, 255, 255),
        font=Font(path="./assets/fonts/Roboto/Roboto-Regular.ttf", size=27)
    )

    # Save the image to a buffer and return it.
    return File(_banner.image_bytes, filename="welcome_message.png")


async def generate_welcome_message_card(
        member: Member,
        loop: AbstractEventLoop = None
) -> File:
    """
    Generates a welcome message card for the given member.

    :param member: The member to generate the card for.
    :param loop: The event loop to use.

    :return: The welcome message card as a :class:`discord.File`.
    """

    loop = loop or get_event_loop()

    try:
        _member_avatar: bytes = await member.avatar.read()
    except AttributeError:
        _member_avatar: bytes = await member.default_avatar.read()
    try:
        _member_banner: bytes = await member.banner.read()
    except AttributeError:
        _member_banner: bytes | None = None

    return await loop.run_in_executor(
        None,
        _generate_welcome_message,
        member.name,
        member.created_at,
        _member_banner,
        _member_avatar,
        member.guild.member_count
    )
