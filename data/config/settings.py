from discord import Intents, Colour

intents: Intents = Intents.default()
intents.__setattr__("members", True)
intents.__setattr__("messages", True)

SETTINGS: dict = {
    "OwnerIDs": [272446903940153345],
    "Description": "A feature-rich bot based on Python 3.9 and Pycord.",
    "Intents": intents,
    "Colours": {
        "Default": Colour.blue(),
        "Error": Colour.red()
    },
    "Cogs": {
        "Experience": {
            "Multiplication": 1,
            "BaseLevel": 250,
            "MinXP": 15,
            "MaxXP": 25,
            "Cooldown": 60,
            "Leaderboard": {
                "ItemsPerPage": 25
            }
        },
        "Music": {
            "MaxQueueLength": 100,
            "MaxDuration": 10800
        }
    },
    "Version": "0.0.1a",
    "Production": False,
    "DatabaseSyncInSeconds": 60
}
