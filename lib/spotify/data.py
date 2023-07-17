from dataclasses import dataclass


@dataclass(init=False)
class SpotifyData:
    """
    A spotify dataclass.

    :ivar id: The Spotify ID of the data.
    :ivar name: The name of the data.
    :ivar url: The URL of the data.
    """

    id: str
    name: str
    url: str

    def __init__(self, data: dict) -> None:
        self.id = data["id"]
        self.name = data["name"]
        self.url = data["external_urls"]["spotify"]

    def __str__(self):
        return self.name
