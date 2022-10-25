from asyncio import Queue
from itertools import islice
from random import shuffle
from typing import Any


class SongQueue(Queue):
    _queue = None

    def __getitem__(self, item) -> Any:
        if isinstance(item, slice):
            return list(islice(self._queue, item.start, item.stop, item.step))
        return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self) -> int:
        return self.qsize()

    def clear(self) -> None:
        self._queue.clear()

    def shuffle(self) -> None:
        shuffle(self._queue)

    def reverse(self) -> None:
        length: int = self.qsize()

        for i in range(int(length / 2)):
            n = self._queue[i]
            self._queue[i] = self._queue[length - i - 1]
            self._queue[length - i - 1] = n

    def remove(self, index: int) -> None:
        del self._queue[index]

    @property
    def duration(self) -> int:
        return sum(song.source.duration for song in self._queue)
