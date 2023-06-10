from enum import Enum

from discord import Embed, Color


class Embeds(Enum):
    """
    A collection of embeds that do not require any additional information.
    """

    YOUTUBE_NOT_ENABLED = Embed(
        title="YouTube is not available",
        description=(
            "Switch to a self hosted bot instance for more customization options.\n"
            "Read more [here](https://www.gamerbraves.com/youtube-forces-discords-rythm-bot-to-shut-down/)."
        ),
        color=Color.brand_red()
    )
