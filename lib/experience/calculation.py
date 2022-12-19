from math import e


def level_size(level: int) -> int:
    """Returns the required xp at a given level."""
    return round(10000 / (1 + 39 * e ** (-0.15 * level))) + 5 * level


def xp_to_level(xp: int) -> tuple[int, int]:
    level: int = 0
    while xp >= level_size(level):
        xp -= level_size(level)
        level += 1
    return level, xp
