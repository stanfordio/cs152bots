from enum import Enum, auto
import discord

class ReportType(Enum):
    OTHER = auto()
    SPAM = auto()
    POSSIBLE_SCAM = auto()
    CANCEL = auto()

# Here we give user different button options to identify the abuse type
class ReportReason(discord.ui.View):

    report_type: ReportType = None

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")
        await self.disable_all_items()

    @discord.ui.button(label="Other", style=discord.ButtonStyle.blurple)
    async def other_option(self, interaction, button):
        await interaction.response.send_message("Taking you to the reporting flow for option other")
        self.report_type = ReportType.OTHER
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Spam", style=discord.ButtonStyle.blurple)
    async def spam_option(self, interaction, button):
        await interaction.response.send_message("Taking you to the reporting flow for Spam")
        self.report_type = ReportType.SPAM
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Possible Scam", style=discord.ButtonStyle.blurple)
    async def possible_spam_option(self, interaction, button):
        await interaction.response.send_message("Taking you to the reporting flow for possible scam")
        self.report_type = ReportType.POSSIBLE_SCAM
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.report_type = ReportType.CANCEL
        await self.disable_all_items()
        self.stop()