from enum import IntEnum


class SongEmbedSize(IntEnum):
    SMALL = 1
    NO_QUEUE = 2
    DEFAULT = 3


class AudioPlayerLoopMode(IntEnum):
    NONE = 0
    QUEUE = 1
    SONG = 2
