class PartialArtist:
    """
    A partial Spotify artist.
    """

    def __init__(self, data: dict) -> None:
        self._id = data["id"]
        self._name = data["name"]
        self._url = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return f"<PartialArtist id={self._id} name={self._name}>"

    def __str__(self) -> str:
        return self._name

    def __eq__(self, other) -> bool:
        return self._id == other.id

    @property
    def id(self) -> str:
        """
        :return: The Spotify ID of the artist.
        """
        return self._id

    @property
    def name(self) -> str:
        """
        :return: The name of the artist.
        """
        return self._name

    @property
    def url(self) -> str:
        """
        :return: The URL of the artist.
        """
        return self._url
