from discord import Intents, Colour

intents: Intents = Intents.default()
intents.__setattr__("members", True)
intents.__setattr__("messages", True)

# Bot settings, apply to all servers. Server specific settings are saved in the database.
SETTINGS: dict = {
    "OwnerIDs": [272446903940153345],  # List of owner IDs
    "Description": "A feature-rich bot based on Python 3.9 and Pycord.",  # Bot description
    "Intents": intents,  # Bot intents
    "Colours": {
        "Default": Colour.blue(),  # Default colour
        "Error": Colour.red(),  # Error colour
        "Special": Colour.gold()  # Event Colour
    },
    "Cogs": {
        "Experience": {
            "Multiplication": 1,  # Multiplication factor for experience gained.
            "BaseLevel": 250,  # Required experience to level 1.
            "MinXP": 15,  # minimum experience per message
            "MaxXP": 25,   # maximum experience per message
            "Cooldown": 60,  # seconds
            "Leaderboard": {
                "ItemsPerPage": 25  # Number of members to show on each page
            }
        },
        "Music": {
            "MaxQueueLength": 100,  # Max amount of songs that can be queued
            "MaxDuration": 10800  # seconds
        },
        "Economy": {
            "WallstreetFee": 0.003
        }
    },
    "Version": "0.0.2a",  # Bot version
    "Production": False,  # If the bot is running in production or not
    "ServiceSyncInSeconds": 500  # How often the bot should sync with the service
}
