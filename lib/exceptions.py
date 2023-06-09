class YouTubeNotEnabled(Exception):
    """Exception raised when the video is on YouTube but YouTube is not enabled."""

    def __init__(self, message: str = "YouTube is not enabled.") -> None:
        self.message = message
        super().__init__(self.message)
