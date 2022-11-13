from data.config.settings import SETTINGS


def level_size(level: int) -> int:
    """Returns the required xp at a given level."""
    return round(SETTINGS["Cogs"]["Experience"]["BaseLevel"] * 1.1248 ** level)
