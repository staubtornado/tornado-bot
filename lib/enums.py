from enum import IntEnum


class SongEmbedSize(IntEnum):
    DEFAULT = 0
    NO_QUEUE = 1
    SMALL = 2

    def __bool__(self) -> bool:
        return True


class AudioPlayerLoopMode(IntEnum):
    NONE = 0
    QUEUE = 1
    SONG = 2
