from lib.spotify.partial_artist import PartialArtist


class Track:
    """
    A Spotify track.
    """

    def __init__(self, data: dict) -> None:
        self._id = data["id"]
        self._title = data["name"]
        self._artists = [PartialArtist(artist) for artist in data["artists"]]
        self._duration = data["duration_ms"] // 1000
        self._url = data["external_urls"]["spotify"]

    @property
    def id(self) -> str:
        """
        :return: The Spotify ID of the track.
        """
        return self.id

    @property
    def title(self) -> str:
        """
        :return: The name of the track.
        """
        return self._title

    @property
    def artists(self) -> list[PartialArtist]:
        """
        :return: The artists of the track.
        """
        return self._artists

    @property
    def artist(self) -> PartialArtist:
        """
        :return: The artist of the track. This is the first artist in the list of artists.
        """
        return self._artists[0]

    @property
    def duration(self) -> int:
        """
        :return: The duration of the track in seconds.
        """
        return self._duration

    @property
    def url(self) -> str:
        """
        :return: The URL of the track.
        """
        return self._url
