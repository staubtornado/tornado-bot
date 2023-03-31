from typing import Any

from discord import Intents, Colour
from requests import get

intents: Intents = Intents.default()
intents.__setattr__("members", True)
intents.__setattr__("messages", True)
intents.__setattr__("message_content", True)

# Bot settings, apply to all servers. Server specific settings are saved in the database.
SETTINGS: dict[str, Any] = {
    "OwnerIDs": [272446903940153345],  # List of owner IDs
    "Description": "A feature-rich bot based on Python 3.11 and Pycord.",  # Bot description
    "Intents": intents,  # Bot intents | DO NOT TOUCH UNLESS YOU KNOW WHAT YOU'RE DOING
    "Colours": {
        "Default": Colour.blue(),  # Default Color
        "Error": Colour.red(),  # Error Color
        "Special": Colour.gold(),  # Event Color
        "Music": 0xFF0000  # Color of song embeds.
    },
    "OwnerGuilds": [795588352387579914],  # List of guild IDs where owner related commands are enabled
    "Cogs": {
        "Experience": {
            "MinXP": 15,  # minimum experience per message
            "MaxXP": 25,   # maximum experience per message
            "Leaderboard": {
                "ItemsPerPage": 19  # Number of members to show on each page
            }
        },
        "Music": {
            "MaxDuration": 10800,  # seconds
            "Queue": {
                "MaxQueueLength": 200,  # Max amount of songs that can be queued
                "ItemsPerPage": 9
            },
            "History": {
                "MaxHistoryLength": 5
            }
        }
    },
    "Version": "0.4.3b",  # Bot version
    "Production": False,  # If the bot is running in production or not
    "ServiceSyncInSeconds": 1800,  # How often the bot should sync with the service
    "ExternalIP": get('https://api.ipify.org').content.decode('utf8'),
    "BetterMusicControlListenOnIP": "127.0.0.1",  # May need to be configured.
    "BetterMusicControlListenOnPort": 65432
}
