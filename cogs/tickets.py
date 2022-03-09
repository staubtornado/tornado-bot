from discord import Bot, ApplicationContext, slash_command, Embed
from discord.ext.commands import Cog

from lib.tickets.views import Support


class Tickets(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.bot.persistent_views_added = False

        if not self.bot.persistent_views_added:
            self.bot.add_view(Support())
            self.bot.persistent_views_added = True

    @slash_command()
    async def send_support_message(self, ctx: ApplicationContext):
        await ctx.send(embed=Embed(title="Create Ticket", description="Create a ticket by clicking the button below."),
                       view=Support())
        await ctx.respond("Done!", ephemeral=False)


def setup(bot: Bot):
    bot.add_cog(Tickets(bot))
