from enum import Enum, auto
import asyncio
from typing import Optional
import discord
from message_util import next_message

class ScamRequestType(Enum):
    MONEY = auto()
    AUTH = auto()
    PERSONAL_INFO = auto()
    NONE = auto()
    OTHER = auto()
    CANCEL = auto()

# Here we ask user if they want to block or mute user who sent them the message
class CheckingScam(discord.ui.View):
    scam_type: ScamRequestType = ScamRequestType.CANCEL
    other_info: str = None

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")
        await self.disable_all_items()

    @discord.ui.button(label="More Info", style=discord.ButtonStyle.gray)
    async def more_info_option(self, interaction, button):
        lines = []
        lines.append("Money: credit or devit card information, money order, cryptocurrency, etc")
        lines.append("Authentication information: Passwords, 2FA codes")
        lines.append("Personally Identifiable information: physical or email address, phone number, SSN, etc")
        await interaction.response.send_message('\n'.join(lines))

    @discord.ui.button(label="Money", style=discord.ButtonStyle.blurple)
    async def money_option(self, interaction, button):
        await interaction.response.send_message("Adding background info to moderation queue item")
        self.scam_type = ScamRequestType.MONEY
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Authentication information", style=discord.ButtonStyle.blurple)
    async def auth_option(self, interaction, button):
        await interaction.response.send_message("Adding background info to moderation queue item")
        self.scam_type = ScamRequestType.AUTH
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Personally identifiable info", style=discord.ButtonStyle.blurple)
    async def pin_option(self, interaction, button):
        await interaction.response.send_message("Adding background info to moderation queue item")
        self.scam_type = ScamRequestType.PERSONAL_INFO
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.blurple)
    async def no_option(self, interaction, button):
        await interaction.response.send_message("Adding background info to moderation queue item")
        self.scam_type = ScamRequestType.NONE
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Other", style=discord.ButtonStyle.blurple)
    async def other_option(self, interaction, button):
        await interaction.response.send_message("What is the user asking for?")
        self.scam_type = ScamRequestType.OTHER
        msg = await next_message()
        if msg == None:
            self.scam_type = ScamRequestType.CANCEL
        else:
            self.other_info = msg.content
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.scam_type = ScamRequestType.CANCEL
        self.stop()