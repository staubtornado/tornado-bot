from discord.ui import View


class QueueFill(View):
    def __init__(self, playlist_length: int) -> None:
        super().__init__(timeout=15)
        self.value = None

