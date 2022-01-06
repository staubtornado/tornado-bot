from discord import Intents, Colour

intents: Intents = Intents.default()
intents.__setattr__("members", True)

SETTINGS: dict = {
    "OwnerIDs": [272446903940153345],
    "Description": "A feature-rich bot based on Python 3.9 and Pycord.",
    "Intents": intents,
    "Colours": {
        "Default": Colour.blue(),
        "Error": Colour.red()
    }
}
