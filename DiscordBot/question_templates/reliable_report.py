from enum import Enum, auto
import discord

class ReportReliability(Enum):
    GOOD = auto()
    BAD = auto()

# Here we give user different button options to identify the abuse type
class ReportIsReliable(discord.ui.View):

    report_reliability: ReportReliability = None

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")
        await self.disable_all_items()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_option(self, interaction, button):
        self.report_reliability = ReportReliability.GOOD
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no_option(self, interaction, button):
        self.report_reliability = ReportReliability.BAD
        await self.disable_all_items()
        self.stop()
