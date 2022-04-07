from discord import ButtonStyle, Interaction
from discord.ui import View, button as ui_button, Button

from lib.tickets.tickets import TicketSystem


class ClosedTicketControl(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui_button(
        label="Delete",
        style=ButtonStyle.danger,
        custom_id="454295622",
    )
    async def delete(self, button: Button, interaction: Interaction):
        await TicketSystem(interaction).delete()

    @ui_button(
        label="Open",
        style=ButtonStyle.green,
        custom_id="824046886",
    )
    async def reopen(self, button: Button, interaction: Interaction):
        await TicketSystem(interaction).open()


class OpenedTicketControl(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui_button(
        label="Close",
        style=ButtonStyle.grey,
        custom_id="715703656",
    )
    async def close(self, button: Button, interaction: Interaction):
        await TicketSystem(interaction).close()

    @ui_button(
        label="Transcript",
        style=ButtonStyle.blurple,
        custom_id="339931015",
    )
    async def transcript(self, button: Button, interaction: Interaction):
        await TicketSystem(interaction).transcript()


class Support(View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui_button(
        label="Create Ticket",
        style=ButtonStyle.green,
        custom_id="516669005",
    )
    async def support(self, button: Button, interaction: Interaction):
        await TicketSystem(interaction).create()
