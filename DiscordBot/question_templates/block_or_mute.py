from enum import Enum, auto
import discord

class BlockOrMuteType(Enum):
    BLOCK = auto()
    MUTE = auto()
    NEITHER = auto()
    CANCEL = auto()

# Here we ask user if they want to block or mute user who sent them the message
class BlockOrMute(discord.ui.View):
    report_type: BlockOrMuteType = None

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
    async def spam_option(self, interaction, button):
        await interaction.response.send_message("Triggering block and adding to moderation queue for review")
        # TODO: Write code that performs the blocking
        self.report_type = BlockOrMuteType.BLOCK
        self.stop()

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.blurple)
    async def possible_spam_option(self, interaction, button):
        await interaction.response.send_message("Triggering mute and adding to moderation queue for review")
        # TODO: Write code that performs Muting
        self.report_type = BlockOrMuteType.MUTE
        self.stop()

    @discord.ui.button(label="Neither", style=discord.ButtonStyle.blurple)
    async def possible_spam_option(self, interaction, button):
        await interaction.response.send_message("Adding to moderation queue for review")
        # TODO: Write code that adds to moderation queue for all
        self.report_type = BlockOrMuteType.NEITHER
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_option(self, interaction, button):
        await interaction.response.send_message("Leaving reporting flow")
        self.report_type = BlockOrMuteType.CANCEL
        self.stop()