class SpotifyException(Exception):
    """Base class for all Spotify errors"""
    pass


class SpotifyNotEnabled(SpotifyException):
    """Exception raised when the content is on Spotify but Spotify is not enabled."""

    def __init__(self, message: str = "Spotify is not enabled.") -> None:
        self.message = message
        super().__init__(self.message)


class SpotifyNotFound(SpotifyException):
    """Exception raised when content is not found."""

    def __init__(self, message: str = "The content was not found.") -> None:
        self.message = message
        super().__init__(self.message)


class SpotifyNotAvailable(SpotifyException):
    """Exception raised when content is not available."""

    def __init__(self, message: str = "The content is not available.") -> None:
        self.message = message
        super().__init__(self.message)


class SpotifyRateLimit(SpotifyException):
    """Exception raised when the rate limit is reached."""

    def __init__(self, message: str = "The rate limit is reached.", *, retry_after: int) -> None:
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)
