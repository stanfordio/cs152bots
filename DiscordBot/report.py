from enum import Enum, auto
import discord
from discord import ui
import re


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()


ABUSE_TYPES = ["Bullying or harassment", "Scam or fraud", "Suicide or self-injury",
                   "Violence or dangerous organizations", "Hate speech or symbols", "Nudity or sexual activity", "Spam", "Other reason"]

class VictimView(ui.View):
    """View to handle who is being harassed."""
    @discord.ui.button(label="Me", style=discord.ButtonStyle.primary)
    async def me_button_callback(self, interaction, button):
        self.disable_buttons()
        button.style = discord.ButtonStyle.success
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("You selected 'Me'.\n\nWhat kinds of harassment did you experience? Select all that apply.")

    @discord.ui.button(label="Someone Else", style=discord.ButtonStyle.secondary)
    async def other_button_callback(self, interaction, button):
        self.disable_buttons()
        button.style = discord.ButtonStyle.success
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("You selected 'Someone Else'.\n\nWho is being bullied?")
    
    def disable_buttons(self):
        """Disables all the buttons in the View and turns them grey."""
        for button in self.children:
            button.disabled = True
            button.style = discord.ButtonStyle.grey


class AbuseSelectView(ui.View):
    """View to handle abuse type selection."""
    @discord.ui.select(placeholder="Select abuse type...", options=[discord.SelectOption(label=abuse) for abuse in ABUSE_TYPES])
    
    async def select_callback(self, interaction, select):
        # TODO: update values

        # Disable Selection
        select.disabled = True
        select.placeholder = select.values[0]
        await interaction.response.edit_message(view=self)

        # Handle flows that are not 'bullying and harassment' differently.
        selection_msg = "You selected " + interaction.data["values"][0].lower() + ".\n\n"
        if (select.values[0] != ABUSE_TYPES[0]):
            await interaction.followup.send(selection_msg + "This is not the flow we specialize in.")
            return

        # Create next view
        next_view = VictimView()
        await interaction.followup.send(selection_msg + "Who is being bullied or harassed?", view=next_view)


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
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            found_msgs = ["I found this message:", "```" + message.author.name + ": " + message.content + "```"]

            # Give options to report
            # button = Button(label="Click me", style=discord.ButtonStyle.green)
            # abuse_type_select = Select(
            #     placeholder="Select abuse type...", options=[discord.SelectOption(label=abuse) for abuse in self.ABUSE_TYPES])

            # async def select_callback(interaction):
            #     self.abuse_type = interaction.data["values"][0]
            #     await interaction.response.edit_message(view=None)
            #     me_button = Button(label="Me", style=discord.ButtonStyle.primary)
            #     other_button = Button(label="Someone Else", style=discord.ButtonStyle.secondary)
            #     next_view = View()
            #     next_view.add_item(me_button)
            #     next_view.add_item(other_button)
            #     next_msg = "Who is being bullied or harassed?"
            #     if (self.abuse_type != self.ABUSE_TYPES[0]):
            #         next_msg = "This is not the flow we specialize in."
            #         await interaction.followup.send("You selected " + interaction.data["values"][0].lower() + ".\n\n" + next_msg)
            #         return
            #     await interaction.followup.send("You selected " + interaction.data["values"][0].lower() + ".\n\n" + next_msg, view=next_view)
            
            # abuse_type_select.callback = select_callback
            # view = View()
            # view.add_item(abuse_type_select)
            view = AbuseSelectView()

            return [*found_msgs, ("Why would you like to report this message?", view)]

        if self.state == State.MESSAGE_IDENTIFIED:
            return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
