from functools import cache
from math import e


def level_size(level: int) -> int:
    """
    Returns the size of the given level.
    """
    return round(10000 / (1 + 39 * e ** (-0.15 * level))) + 5 * level


@cache
def xp_to_level(xp: int) -> tuple[int, int]:
    """
    Returns the level and the experience of the given experience.

    :param xp: The experience to convert.

    :return: A tuple containing the experience and the level.
    """

    level: int = 0
    while xp >= level_size(level):
        xp -= level_size(level)
        level += 1
    return xp, level
