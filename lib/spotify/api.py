from datetime import datetime, timedelta
from re import match
from time import time
from typing import AsyncGenerator, Any
from urllib.parse import quote

from aiohttp import ClientSession, ClientResponse

from lib.spotify.album import Album
from lib.spotify.artist import Artist
from lib.spotify.data import SpotifyData
from lib.spotify.exceptions import SpotifyRateLimit, SpotifyNotFound, SpotifyNotAvailable
from lib.spotify.playlist import Playlist
from lib.spotify.track import Track


class SpotifyAPI:
    """
    A Spotify API client. Lightweight wrapper around the Spotify Web API.
    """

    _trending_playlists: tuple[dict[str, Any] | None, float]

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None

        self._retry_after = None

        self._trending_playlists = (None, 0.0)

    async def _get_token(self) -> None:
        async with ClientSession() as session:
            async with session.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret
                }
            ) as response:
                data = await response.json()
                self._token = data["access_token"]

    @staticmethod
    def _strip_url(url: str) -> str:
        m = match(r"(https://)?open.spotify\.com/(intl-\w+/)?(track|album|artist|playlist)/(\w+)", url)
        if m:
            return m.group(4)
        raise ValueError("Invalid Spotify URL")

    def _validate_response_status(self, response: ClientResponse) -> None:
        match response.status:
            case 429:  # Rate limit
                self._retry_after = datetime.now() + timedelta(seconds=int(response.headers["Retry-After"]))
                raise SpotifyRateLimit(retry_after=int(response.headers["Retry-After"]))
            case 200:  # OK
                pass
            case 404:  # No content
                raise SpotifyNotFound()
            case _:
                raise SpotifyNotAvailable(response.reason)

    async def _get(self, url: str) -> dict:
        if not self._token:
            await self._get_token()

        if self._retry_after and datetime.now() < self._retry_after:
            raise SpotifyRateLimit(retry_after=(self._retry_after - datetime.now()).seconds)
        self._retry_after = None

        async with ClientSession() as session:
            async with session.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}"
                }
            ) as response:
                self._validate_response_status(response)
                return await response.json()

    async def get_track(self, track_id: str) -> Track:
        """
        :param track_id: The Spotify ID of the track.
        :return: The track.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the track could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if "https://open.spotify.com/" in track_id:
            track_id = self._strip_url(track_id)

        response: dict = await self._get(f"https://api.spotify.com/v1/tracks/{track_id}")
        return Track(response)

    async def get_album(self, album_id: str) -> Album:
        """
        :param album_id: The Spotify ID of the album.
        :return: The album.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the album could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if "https://open.spotify.com/" in album_id:
            album_id = self._strip_url(album_id)

        response: dict = await self._get(f"https://api.spotify.com/v1/albums/{album_id}")
        return Album(response)

    async def get_artist(self, artist_id: str) -> Artist:
        """
        :param artist_id: The Spotify ID of the artist.
        :return: The artist.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the artist could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if "https://open.spotify.com/" in artist_id:
            artist_id = self._strip_url(artist_id)

        response: dict = await self._get(f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=DE")
        return Artist(response)

    async def get_playlist_tracks(self, playlist_id: str, start: int, end: int) -> list[Track]:
        """
        :param playlist_id: The Spotify ID of the playlist.
        :param start: The start index of the tracks to retrieve.
        :param end: The end index of the tracks to retrieve.
        :return: A list of tracks in the specified range.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the playlist could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if "https://open.spotify.com/" in playlist_id:
            playlist_id = self._strip_url(playlist_id)

        tracks: list[Track] = []
        while start < end:
            limit = min(end - start, 50)
            response = await self._get(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={start}&limit={limit}")
            tracks.extend([Track(item["track"]) for item in response["items"]])
            start += limit

        return tracks

    async def get_playlist(self, playlist_id: str) -> Playlist:
        """
        :param playlist_id: The Spotify ID of the playlist.
        :return: The playlist.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the playlist could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if "https://open.spotify.com/" in playlist_id:
            playlist_id = self._strip_url(playlist_id)

        response: dict = await self._get(f"https://api.spotify.com/v1/playlists/{playlist_id}")
        return Playlist(response)

    async def search(self, query: str, limit: int = 10) -> AsyncGenerator[Track, None]:
        """
        :param query: The query to search for.
        :param limit: The maximum number of results to fetch.
        :return: The search results.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the search results could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """
        query = quote(query)
        response: dict = await self._get(f"https://api.spotify.com/v1/search?q={query}&type=track&limit={limit}")
        for track in response["tracks"]["items"]:
            yield Track(track)

    async def get_trending_playlists(self, use_cache: bool = True) -> list[SpotifyData]:
        """
        :return: The trending playlists.

        :param use_cache: Whether to use the cached response.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the trending playlists could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if use_cache:
            # Check if there are already trending playlists cached and if they are older than 24 hours
            if not self._trending_playlists[0] or time() - self._trending_playlists[1] > 86400:
                use_cache = False

        if not use_cache:
            response: dict = await self._get("https://api.spotify.com/v1/browse/featured-playlists")
            self._trending_playlists = (response["playlists"]["items"], time())
        return [SpotifyData(playlist) for playlist in self._trending_playlists[0]]
