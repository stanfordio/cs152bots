from enum import Enum, auto
import discord
from discord.ui import Button, View, Select
import re


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    ABUSE_TYPES = ["Bullying or harassment", "Scam or fraud", "Suicide or self-injury",
                   "Violence or dangerous organizations", "Hate speech or symbols", "Nudity or sexual activity", "Spam", "Other reason"]

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuse_type = None

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return [("Report cancelled.", None)]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [(reply, None)]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return [("I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel.", None)]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [("I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again.", None)]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [("It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel.", None)]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [("It seems this message was deleted or never existed. Please try again or say `cancel` to cancel.", None)]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            found_msgs = [("I found this message:", None), ("```" +
                                                            message.author.name + ": " + message.content + "```", None)]

            # Give options to report
            # button = Button(label="Click me", style=discord.ButtonStyle.green)
            abuse_type_select = Select(
                placeholder="Select abuse type...", options=[discord.SelectOption(label=abuse) for abuse in self.ABUSE_TYPES])

            async def select_callback(interaction):
                self.abuse_type = interaction.data["values"][0]
                await interaction.response.edit_message(view=None)
                await interaction.followup.send("You selected " + interaction.data["values"][0].lower() + ".")
            
            abuse_type_select.callback = select_callback
            view = View()
            view.add_item(abuse_type_select)

            return [*found_msgs, ("Why would you like to report this message?", view)]

        if self.state == State.MESSAGE_IDENTIFIED:
            return [("<insert rest of reporting flow here>", None)]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
