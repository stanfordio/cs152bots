from enum import Enum, auto
from message_util import next_message
import discord

class IsImpersonation(Enum):
    NO = auto()
    YES = auto()
    CANCEL = auto()

# Here we give user different button options to identify the abuse type
class PossibleImpersonation(discord.ui.View):

    is_impersonating: IsImpersonation = IsImpersonation.CANCEL

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")
        await self.disable_all_items()


    @discord.ui.button(label="Yes", style=discord.ButtonStyle.blurple)
    async def yes_option(self, interaction, button):
        self.is_impersonating = IsImpersonation.YES
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.blurple)
    async def no_option(self, interaction, button):
        self.is_impersonating = IsImpersonation.NO
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.report_type = IsImpersonation.CANCEL
        await self.disable_all_items()
        self.stop()