from io import BytesIO
from typing import Union, Any

from PIL import Image
from discord import Member
from easy_pil import Editor, Font
from numpy import average


async def generate_welcome_message(member: Member):
    banner: bool = False

    if member.banner is not None:
        background: bytes = await member.banner.read()
        banner = True
    else:
        try:
            background: bytes = await member.avatar.read()
        except AttributeError:
            background: bytes = await member.default_avatar.read()

    image: Image = Image.open(BytesIO(background))
    colors: list[Union[tuple[int, tuple[int, ...]], Any]] = image.getcolors(maxcolors=image.height * image.width)

    if not banner:
        r: list[int] = []
        g: list[int] = []
        b: list[int] = []
        a: list[int] = []

        for color in colors:
            r.append(color[1][0])
            g.append(color[1][1])
            b.append(color[1][2])
            a.append(color[1][3])

        image = Image.new(
            mode="RGBA",
            size=(600, 400),
            color=(
                int(average(r, axis=0)),
                int(average(g, axis=0)),
                int(average(b, axis=0)),
                int(average(a, axis=0))
            )
        )

    if banner:
        try:
            background = await member.avatar.read()
        except AttributeError:
            background = await member.default_avatar.read()
    avatar: Editor = Editor(Image.open(BytesIO(background)))
    avatar.resize((200, 200))
    avatar.circle_image()

    editor: Editor = Editor(image)
    editor.rounded_corners()
    editor.paste(avatar, (200, 50))
    editor.text((100, 300), text=f"{member} joined the server!", font=Font(path="./assets/font.ttf", size=20))
    editor.show()
