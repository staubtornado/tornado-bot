from io import BytesIO
from random import randint, randrange
from time import strftime, gmtime

from millify import millify
from PIL import Image
from colorthief import ColorThief


def ordinal(n: int) -> str:
    """Returns the ordinal suffix for a number."""
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


def format_time(seconds: int) -> str:
    """Formats a time in seconds to a human-readable format."""
    if seconds < 3600:
        return strftime("%M:%S", gmtime(seconds))
    elif 86400 > seconds >= 3600:
        return strftime("%H:%M:%S", gmtime(seconds))
    return strftime("%H:%M:%S", gmtime(seconds))


def shortened(n: int) -> str:
    """Shortens a number to a human-readable format."""
    return millify(n, precision=1, drop_nulls=True)


def truncate(s: str, limit: int, ending: str = "...") -> str:
    """Shortens a string to a certain limit and adds an ending."""
    return s[:limit - len(ending)] + ending if len(s) > limit else s


def random_hex(length: int) -> str:
    """Generates a random hex string."""
    return f'{randrange(16**length):x}'.zfill(length)


def dominant_color(image: bytes) -> tuple[int, int, int]:
    """
    Gets the average color of an image.

    :param image: The image to get the average color of.

    :return: The average color of the image.
    """
    
    color_thief = ColorThief(BytesIO(image))

    # get the dominant color
    dominant_color = color_thief.get_color(quality=1)
    return dominant_color

    
    

    # 
    

    

