from enum import Enum, auto
import discord

class SpamRequestType(Enum):
    MONEY = auto()
    AUTH = auto()
    PERSONAL_INFO = auto()
    OTHER = auto()
    CANCEL = auto()

# Here we ask user if they want to block or mute user who sent them the message
class CheckingSpam(discord.ui.View):
    report_type: SpamRequestType = None

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")
        await self.disable_all_items()

    @discord.ui.button(label="MORE_INFO", style=discord.ButtonStyle.gray)
    async def other_option(self, interaction, button):
        lines = []
        lines.append("Money: credit or devit card information, money order, cryptocurrency, etc")
        lines.append("Authentication information: Passwords, 2FA codes")
        lines.append("Personally Identifiable information: physical or email address, phone number, SSN, etc")
        await interaction.response.send_message('\n'.join(lines))

    @discord.ui.button(label="Money", style=discord.ButtonStyle.blurple)
    async def spam_option(self, interaction, button):
        await interaction.response.send_message("Adding background infor to moderation queue item")
        self.report_type = SpamRequestType.MONEY
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Authentication information", style=discord.ButtonStyle.blurple)
    async def possible_spam_option(self, interaction, button):
        await interaction.response.send_message("Adding background infor to moderation queue item")
        self.report_type = SpamRequestType.AUTH
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Personally identifiable info", style=discord.ButtonStyle.blurple)
    async def possible_spam_option(self, interaction, button):
        await interaction.response.send_message("Adding background infor to moderation queue item")
        self.report_type = SpamRequestType.PERSONAL_INFO
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Other", style=discord.ButtonStyle.blurple)
    async def possible_spam_option(self, interaction, button):
        await interaction.response.send_message("Adding background infor to moderation queue item")
        self.report_type = SpamRequestType.OTHER
        #TODO: Ask user to type out reason
        await self.disable_all_items()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.report_type = SpamRequestType.CANCEL
        self.stop()