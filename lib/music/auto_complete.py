from urllib.parse import urlparse

from lib.contexts import CustomAutocompleteContext


async def complete(ctx: CustomAutocompleteContext) -> list[str]:
    """
    Autocomplete for the /play and /playnext command.

    :param ctx: The context of the command.
    :return: A list of possible completions.
    """

    results: list[str] = []
    value = ctx.value

    if not len(value) > 3:
        if ctx.command.name == "playnext":
            return []

        for playlist in await ctx.bot.spotify.get_trending_playlists():
            results.append(f"Playlist: {playlist.name}")
        return results
    
    # Check if the value is any url
    if urlparse(value).scheme in ["http", "https"]:
        return []
    return [f"{track.name} {track.artists[0]}"[:100] async for track in ctx.bot.spotify.search(value, limit=10)]
