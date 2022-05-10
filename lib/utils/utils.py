from discord import AutocompleteContext
from millify import millify


def ordinal(n: int or float) -> str:
    if isinstance(n, float):
        n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


def shortened(n: int or float, precision: int = 2) -> str:
    return millify(n, precision=precision)


async def auto_complete(ctx: AutocompleteContext) -> list:
    return ["Charts", "New Releases", "Chill", "Party", "Classical", "K-Pop", "Gaming", "Rock"]
