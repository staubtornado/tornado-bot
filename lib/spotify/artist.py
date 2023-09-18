from lib.spotify.data import SpotifyData
from lib.spotify.track_collection import TrackCollection


class Artist(SpotifyData, TrackCollection):
    """
    A Spotify artist.
    """

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        TrackCollection.__init__(self, data)
