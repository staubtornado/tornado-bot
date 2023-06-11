from asyncio import Queue
from collections import deque
from itertools import islice
from random import shuffle

from lib.music.song import Song


class SongQueue(Queue):
    _queue: deque

    def __init__(self, maxsize: int = 0) -> None:
        super().__init__(maxsize)

    def __repr__(self) -> str:
        return f"<SongQueue maxsize={self.maxsize} qsize={self.qsize()}>"

    def __getitem__(self, item: int) -> Song | list[Song]:
        if isinstance(item, slice):
            return list(islice(self._queue, item.start, item.stop, item.step))
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

    def insert(self, index: int, item: Song) -> None:
        self._queue.insert(index, item)

    @property
    def duration(self) -> int:
        return sum(song.duration for song in self._queue)
