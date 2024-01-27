from dataclasses import dataclass
from typing import Iterator, Self

from lib.spotify.track import Track


@dataclass()
class TrackCollection:
    """
    :ivar tracks: The tracks in the collection.
    :ivar total: The total number of tracks in the collection.
    This may be greater than the number of tracks processed in the collection.
    """

    tracks: list[Track]
    total: int

    def __init__(self, data: dict) -> None:
        if isinstance(data.get("tracks"), dict):
            self.tracks = [Track(track) for track in data["tracks"]["items"]]
            self.total = data["tracks"]["total"]
        else:
            self.tracks = [Track(track) for track in data["tracks"]]
            self.total = len(self.tracks)

    def __len__(self) -> int:
        return len(self.tracks)

    def __getitem__(self, index: int | slice) -> Track | list[Track]:
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
