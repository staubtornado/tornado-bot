from dataclasses import dataclass
from typing import Iterator, Self

from lib.spotify.track import Track


@dataclass()
class TrackCollection:
    """
    :ivar tracks: The tracks in the collection.
    """

    tracks: list[Track]

    def __init__(self, data: dict) -> None:
        self.tracks = [Track(track['track']) for track in data["tracks"]["items"]]

    def __len__(self) -> int:
        return len(self.tracks)

    def __getitem__(self, index: int) -> Track:
        return self.tracks[index]

    def __iter__(self) -> Iterator[Track]:
        return iter(self.tracks)

    def __contains__(self, item: Track) -> bool:
        return item in self.tracks

    def __iadd__(self, other) -> Self:
        self.tracks += other.tracks
        return self

    @property
    def duration(self) -> int:
        """
        :return: The total duration of the collection in seconds.
        """
        return sum(track.duration for track in self.tracks)
