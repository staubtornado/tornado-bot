from asyncio import Queue
from collections import deque
from random import shuffle
from typing import Union

from lib.music.song import Song
from lib.spotify.track import Track


class SongQueue(Queue):
    _queue: deque

    def __init__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize)

    def __repr__(self) -> str:
        return f"<SongQueue maxsize={self.maxsize} qsize={self.qsize()}>"

    def __getitem__(self, item: int) -> Union[Song, Track]:
        return self._queue[item]

    def __iter__(self) -> iter:
        return iter(self._queue)

    def __len__(self) -> int:
        return len(self._queue)

    def __reversed__(self):
        return reversed(self._queue)

    def __setitem__(self, key, value) -> None:
        self._queue[key] = value

    def __delitem__(self, key) -> None:
        del self._queue[key]

    def __contains__(self, item) -> bool:
        return item in self._queue

    def shuffle(self) -> None:
        shuffle(self._queue)

    def clear(self) -> None:
        self._queue.clear()
