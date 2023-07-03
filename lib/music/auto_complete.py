from lib.contexts import CustomAutocompleteContext


async def complete(ctx: CustomAutocompleteContext) -> list[str]:
    """
    Autocomplete for the /play command.

    :param ctx: The context of the command.
    :return: A list of possible completions.
    """

    results: list[str] = []
    value = ctx.value

    if not len(value) > 3:
        return results
    return [f"{track.title} {track.artists[0]}"[:100] async for track in ctx.bot.spotify.search(value, limit=10)]
