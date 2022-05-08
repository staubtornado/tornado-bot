from asyncio import Queue
from itertools import islice
from random import shuffle

from lib.music.song import Song


class SongQueue(Queue):
    _queue = None

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(islice(self._queue, item.start, item.stop, item.step))
        return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        shuffle(self._queue)

    def reverse(self):
        length: int = self.qsize()

        for i in range(int(length / 2)):
            n = self._queue[i]
            self._queue[i] = self._queue[length - i - 1]
            self._queue[length - i - 1] = n

    def remove(self, index: int):
        del self._queue[index]

    def get_duration(self) -> int:
        duration = 0

        for song in self._queue:
            if isinstance(song, Song):
                duration += int(song.source.data.get("duration"))
                continue
            duration += 210
        return duration
