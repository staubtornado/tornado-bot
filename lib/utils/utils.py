from discord import AutocompleteContext


def ordinal(n: int or float) -> str:
    if isinstance(n, float):
        n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


async def auto_complete(ctx: AutocompleteContext) -> list:
    return ["Charts", "New Releases", "Chill", "Party", "Classical", "K-Pop", "Gaming", "Rock"]
