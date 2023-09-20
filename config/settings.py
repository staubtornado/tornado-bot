from typing import Any

from discord import Intents

intents = Intents.default()
intents.__setattr__("members", True)
intents.__setattr__("messages", True)


SETTINGS: dict[str, Any] = {
    'Music': {
        'YouTubeEnabled': False
    },
    'OwnerIDs': [
        272446903940153345
    ],
    'Description': '',
    'Intents': intents,
    "Version": "0.5.1b",
}

