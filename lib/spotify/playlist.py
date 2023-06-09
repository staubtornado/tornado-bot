from typing import Iterator

from lib.spotify.track import Track
from lib.spotify.track_collection import TrackCollection


class Playlist(TrackCollection):
    """
    A Spotify playlist.
    """
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self._tracks = [Track(track['track']) for track in data["tracks"]["items"]]
