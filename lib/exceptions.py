class YouTubeNotEnabled(Exception):
    """Exception raised when the video is on YouTube but YouTube is not enabled."""

    def __init__(self, message: str = "YouTube is not enabled.") -> None:
        self.message = message
        super().__init__(self.message)


class NotEnoughVotes(Exception):
    """Exception raised when there are not enough votes to pass a voting."""

    def __init__(self, message: str = "Not enough votes to skip.") -> None:
        self.message = message
        super().__init__(self.message)
