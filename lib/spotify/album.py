from lib.spotify.track import Track
from lib.spotify.track_collection import TrackCollection


class Album(TrackCollection):
    """
    A Spotify album.
    """
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self._tracks = [Track(track) for track in data["tracks"]["items"]]
