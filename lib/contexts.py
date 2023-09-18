from discord import ApplicationContext, Member, Interaction, AutocompleteContext

from bot import TornadoBot


class CustomApplicationContext(ApplicationContext):
    bot: TornadoBot

    author: Member  # Used to fix issues with the author property in slash commands

    def __init__(self, bot: TornadoBot, interaction: Interaction) -> None:
        super().__init__(bot, interaction)


class CustomAutocompleteContext(AutocompleteContext):
    bot: TornadoBot

    def __init__(self, bot: TornadoBot, interaction: Interaction) -> None:
        super().__init__(bot, interaction)
