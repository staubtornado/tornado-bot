from lib.spotify.partial_artist import PartialArtist
from lib.spotify.track import Track


class Artist(PartialArtist):
    """
    A Spotify artist.
    """

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self._top_tracks = [Track(track) for track in data["top_tracks"]]

    @property
    def top_tracks(self) -> list[Track]:
        """
        :return: The top tracks of the artist.
        """
        return self._top_tracks
