from lib.spotify.data import SpotifyData


class Track(SpotifyData):
    """
    A Spotify track.
    """

    def __init__(self, data: dict) -> None:
        if isinstance(data.get("track"), dict):
            data = data["track"]

        super().__init__(data)
        self._artists = [SpotifyData(artist) for artist in data["artists"]]
        self._duration = data["duration_ms"] // 1000

    @property
    def duration(self) -> int:
        """
        :return: The duration of the track in seconds.
        """
        return self._duration

    @property
    def artists(self) -> list[SpotifyData]:
        """
        :return: The artists of the track.
        """
        return self._artists
