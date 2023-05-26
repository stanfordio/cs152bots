from enum import Enum, auto
from message_util import next_message
import discord

class PossibleImpersonationType(Enum):
    TECH_SUPPORT = auto()
    GOVERNMENT = auto()
    PROFESSIONAL = auto()
    SOMEONE_I_KNOW = auto()
    OTHER = auto()
    NEVERMIND = auto()
    CANCEL = auto()

# Here we give user different button options to identify the abuse type
class PossibleImpersonation(discord.ui.View):

    impersonation_type: PossibleImpersonationType = None
    impersontator_info: str = None

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")
        await self.disable_all_items()

    @discord.ui.button(label="TechSupport", style=discord.ButtonStyle.blurple)
    async def tech_option(self, interaction, button):
        await interaction.response.send_message("Thank you for letting us know. Note that no tech support firm or IT departments will need to ask you for your password or any authentication information.")
        await interaction.response.send_message("Please provide the name of the company they were claiming to be from.")
        self.impersonation_type = PossibleImpersonationType.TECH_SUPPORT
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Government / LE", style=discord.ButtonStyle.blurple)
    async def gov_option(self, interaction, button):
        await interaction.response.send_message("Please provide the name of the agency they claim to represent")
        self.impersonation_type = PossibleImpersonationType.GOVERNMENT
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Professional", style=discord.ButtonStyle.blurple)
    async def professional_option(self, interaction, button):
        await interaction.response.send_message("Please provide the name of the agency they claim to represent")
        self.impersonation_type = PossibleImpersonationType.PROFESSIONAL
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Someone I Know", style=discord.ButtonStyle.blurple)
    async def someone_option(self, interaction, button):
        await interaction.response.send_message("Please provide the name of the agency they claim to represent")
        self.impersonation_type = PossibleImpersonationType.SOMEONE_I_KNOW
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Other", style=discord.ButtonStyle.blurple)
    async def other_option(self, interaction, button):
        await interaction.response.send_message("What is the user asking for?")
        self.scam_type = PossibleImpersonationType.OTHER
        msg = await next_message()
        if msg == None:
            self.impersonation_type = PossibleImpersonationType.CANCEL
        else:
            self.other_info = msg.content
        await self.disable_all_items()
        self.stop()
    # TODO: Add the rest of the options

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.report_type = PossibleImpersonationType.CANCEL
        await self.disable_all_items()
        self.stop()