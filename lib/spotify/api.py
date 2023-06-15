from datetime import datetime, timedelta
from re import match
from typing import AsyncGenerator
from urllib.parse import quote

from aiohttp import ClientSession, ClientResponse

from lib.spotify.album import Album
from lib.spotify.artist import Artist
from lib.spotify.exceptions import SpotifyRateLimit, SpotifyNotFound, SpotifyNotAvailable
from lib.spotify.playlist import Playlist
from lib.spotify.track import Track


class SpotifyAPI:
    """
    A Spotify API client. Lightweight wrapper around the Spotify Web API.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None

        self._retry_after = None

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

    async def get_playlist(self, playlist_id: str, limit: int = 400) -> Playlist:
        """
        :param playlist_id: The Spotify ID of the playlist.
        :param limit: The maximum number of tracks to fetch.
        :return: The playlist.

        :raises SpotifyRateLimit: If the rate limit is exceeded.
        :raises SpotifyNotFound: If the playlist could not be found.
        :raises SpotifyNotAvailable: If the Spotify API is not available.

        Note: All raised exceptions are subclasses of :class:`SpotifyException`.
        """

        if "https://open.spotify.com/" in playlist_id:
            playlist_id = self._strip_url(playlist_id)

        response: dict = await self._get(f"https://api.spotify.com/v1/playlists/{playlist_id}")
        playlist = Playlist(response)

        for i in range(100, limit, 50):
            _response: dict = await self._get(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={i}&limit=50"
            )
            response['tracks']["items"] = _response["items"]
            playlist += Playlist(response)
            if i + 50 >= _response["total"]:
                break
        return playlist

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
