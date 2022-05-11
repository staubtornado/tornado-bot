from discord import ButtonStyle, Interaction
from discord.ui import View, button as ui_button, Button


class ConfirmTransaction(View):
    def __init__(self):
        super().__init__()
        self.value = None

    @ui_button(
        label="Confirm",
        style=ButtonStyle.green,
        custom_id="845997145"
    )
    async def confirm(self, button: Button, interaction: Interaction):
        self.value = True
        self.stop()

    @ui_button(
        label="Cancel",
        style=ButtonStyle.red,
        custom_id="851715352"
    )
    async def cancel(self, button: Button, interaction: Interaction):
        self.value = False
        self.stop()
