from enum import Enum, auto
import discord

class BlockOrMuteType(Enum):
    BLOCK = auto()
    MUTE = auto()
    NEITHER = auto()
    CANCEL = auto()

# Here we ask user if they want to block or mute user who sent them the message
class BlockOrMute(discord.ui.View):
    requested_response_type: BlockOrMuteType = BlockOrMuteType.CANCEL
    

    async def disable_all_items(self):
        for item in self.children:
            item.disabled=True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.message.channel.send("Timedout")

    @discord.ui.button(label="MORE_INFO", style=discord.ButtonStyle.gray)
    async def other_option(self, interaction, button):
        await interaction.response.send_message("Muting a user will still allow them to send messages to you, but they will not appear\
                                                in your inbox.\n Blocking a user will prevent them from sending messages to you.")

    @discord.ui.button(label="Block", style=discord.ButtonStyle.blurple)
    async def scam_option(self, interaction, button):
        await interaction.response.send_message("Triggering block and adding to moderation queue for review")
        self.requested_response_type = BlockOrMuteType.BLOCK
        self.stop()

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.blurple)
    async def mute_option(self, interaction, button):
        await interaction.response.send_message("Triggering mute and adding to moderation queue for review")
        self.requested_response_type = BlockOrMuteType.MUTE
        self.stop()

    @discord.ui.button(label="Neither", style=discord.ButtonStyle.blurple)
    async def neither_option(self, interaction, button):
        await interaction.response.send_message("Adding to moderation queue for review")
        self.requested_response_type = BlockOrMuteType.NEITHER
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.requested_response_type = BlockOrMuteType.CANCEL
        self.stop()