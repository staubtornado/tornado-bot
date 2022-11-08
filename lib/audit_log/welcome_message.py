from io import BytesIO
from typing import Union, Any

from PIL import Image
from discord import Member
from easy_pil import Editor, Font
from numpy import average

from lib.utils.utils import ordinal


async def generate_welcome_message(member: Member):
    try:
        background: bytes = await member.avatar.read()
    except AttributeError:
        background: bytes = await member.default_avatar.read()

    image: Image = Image.open(BytesIO(background))
    colors: list[Union[tuple[int, tuple[int, ...]], Any]] = image.getcolors(maxcolors=image.height * image.width)

    r: list[int] = []
    g: list[int] = []
    b: list[int] = []
    a: list[int] = []

    for _color in colors:
        r.append(_color[1][0])
        g.append(_color[1][1])
        b.append(_color[1][2])
        a.append(_color[1][3])
    color: tuple[int, ...] = (
        int(average(r, axis=0)),
        int(average(g, axis=0)),
        int(average(b, axis=0)),
        int(average(a, axis=0))
    )

    image = Image.new(
        mode="RGBA",
        size=(1100, 500),
        color=color
    )

    avatar: Editor = Editor(Image.open(BytesIO(background)))
    avatar.resize((256, 256))
    avatar.circle_image()

    editor: Editor = Editor(image)
    editor.rounded_corners()
    editor.paste(avatar, (422, 50))
    editor.ellipse(
        position=(416, 44),
        width=268,
        height=268,
        outline=(79, 84, 92),
        stroke_width=7
    )

    text_color: tuple[int, int, int] = (255, 255, 255)
    if (color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114) > 186:  # https://stackoverflow.com/a/3943023
        text_color = (0, 0, 0)

    editor.text(
        position=(550, 376),
        text=f"{member} joined the server!",
        font=Font(path="./assets/font.ttf", size=40),
        align="center",
        color=text_color
    )
    editor.text(
        position=(550, 423),
        text=f"{ordinal(len(member.guild.members))} Member",
        font=Font(path="./assets/font.ttf", size=32),
        align="center",
        color=text_color
    )
    editor.save("./test.png", format="PNG")
