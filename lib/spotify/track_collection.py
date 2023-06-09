from typing import Iterator, Self

from lib.spotify.track import Track


class TrackCollection:
    """
    A collection of tracks. This class is not meant to be instantiated directly.
    """
    _tracks: list[Track]

    def __init__(self, data: dict) -> None:
        self._id = data["id"]
        self._name = data["name"]
        self._url = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return f"<Playlist id={self._id} name={self._name}>"

    def __str__(self) -> str:
        return self._name

    def __eq__(self, other) -> bool:
        return self._id == other.id

    def __len__(self) -> int:
        return len(self._tracks)

    def __getitem__(self, index: int) -> Track:
        return self._tracks[index]

    def __iter__(self) -> Iterator[Track]:
        return iter(self._tracks)

    def __contains__(self, item: Track) -> bool:
        return item in self._tracks

    def __iadd__(self, other) -> Self:
        self._tracks += other.tracks
        return self

    @property
    def id(self) -> str:
        """
        :return: The Spotify ID of the playlist.
        """
        return self._id

    @property
    def name(self) -> str:
        """
        :return: The name of the playlist.
        """
        return self._name

    @property
    def url(self) -> str:
        """
        :return: The URL of the playlist.
        """
        return self._url

    @property
    def tracks(self) -> list[Track]:
        """
        :return: The tracks in the playlist.
        """
        return self._tracks

    @property
    def duration(self) -> int:
        """
        :return: The total duration of the playlist in seconds.
        """
        return sum(track.duration for track in self._tracks)
