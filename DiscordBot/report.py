from enum import Enum, auto
import discord
from discord.components import SelectOption
from discord.ui import Select, View
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    AWAITING_BLOCK_CONSENT = auto()
    AWAITING_SCAM_INFO = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    BLOCK_USER_MESSAGE = "Would you like to block the user so they cannot message you in the future? (y/n)"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

    def get_report_view(self):
        options = [
            SelectOption(emoji="📫", label='Blackmail', value='Blackmail'),
            SelectOption(emoji="💰", label='Investment Scam', value='Investment Scam'),
            SelectOption(emoji="🔗", label='Suspicious Link', value='Suspicious Link'),
            SelectOption(emoji="⚠️", label="Imminent Danger", value="Imminent Danger")
        ]

        dropdown = Select(
            placeholder='Select a reason',
            options=options,
            custom_id='report_reason_dropdown'
        )

        async def my_callback(interaction):
            if dropdown.values[0] == 'Suspicious Link':
                await interaction.response.send_message(f"Thank you for reporting. Our content moderation team will review the link and flag it if necessary.\n{Report.BLOCK_USER_MESSAGE}")
                self.state = State.AWAITING_BLOCK_CONSENT
            elif dropdown.values[0] == 'Blackmail':
                await interaction.response.send_message(f"Please select the form(s) of blackmail", view=self.get_blackmail_view())
            elif dropdown.values[0] == "Investment Scam":
                await interaction.response.send_message(f"Please select all that applies", view=self.get_scam_view())
            elif dropdown.values[0] == "Imminent Danger":
                await interaction.response.send_message(f"If you are in a life-threatening situation, please contact your local authorities.\nOur content moderation team will review the message and decide on an appropriate action. This may include working with the local authorities and providing message content.\n{Report.BLOCK_USER_MESSAGE}")
                self.state = State.AWAITING_BLOCK_CONSENT
            else:
                await interaction.response.send_message(f"You chose: {dropdown.values[0]}")

        dropdown.callback = my_callback
        view = View()
        view.add_item(dropdown)
        return view

    def get_scam_view(self):
        options = [
            SelectOption(label='Assets Sent', value='Assets Sent', description="You have sent money or cryptocurrency."),
            SelectOption(label='Personal Information Provided' , value='Personal Information Provided', description="You have provided personal information such as bank information, account login, etc."),
            SelectOption(label='Suspicion of Impersonation', value='Suspicion of Impersonation', description="You believe the account is fraudulent."),
        ]

        dropdown = Select(
            min_values=1,
            max_values=3,
            placeholder='Select all that applies',
            options=options,
            custom_id='scam_dropdown'
        )

        async def my_callback(interaction):
            await interaction.response.send_message(f"Thank you for reporting. Our content moderation team will review the message and decide on an appropriate action. \nPlease provide any other useful information that could help our investigation, such as date of transactions, specific information that was sent, how much assets were lost. If no additional information can be provided, reply with N/A.")
            self.state = State.AWAITING_SCAM_INFO

        dropdown.callback = my_callback
        view = View()
        view.add_item(dropdown)
        return view

    def get_blackmail_view(self):
        options = [
            SelectOption(label='Reveal Explicit Content', value='Explicit Content'),
            SelectOption(label='Reveal Personal/Sensitive Information', value='Personal/Sensitive Information'),
            SelectOption(label='Threat to do Physical Harm', value='Threat to do Physical Harm'),
        ]

        dropdown = Select(
            min_values=1,
            max_values=3,
            placeholder='Select form(s) of threat',
            options=options,
            custom_id='blackmail_dropdown'
        )

        async def my_callback(interaction):
            await interaction.response.send_message(f"Thank you for reporting. Our content moderation team will review the message and decide on an appropriate action. This may include removing the user from our platform.\n{Report.BLOCK_USER_MESSAGE}")
            self.state = State.AWAITING_BLOCK_CONSENT

        dropdown.callback = my_callback
        view = View()
        view.add_item(dropdown)
        return view

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return [{"response": "Report cancelled."}]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [{"response": reply}]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return [{"response": "I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."}]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [{"response": "I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."}]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [{"response": "It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."}]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [{"response": "It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."}]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED

            return [{"response": "I found this message:"},
                    {"response": "```" + message.author.name + ": " + message.content + "```"},
                    {"response": "Please select the reason for reporting this message.", "view": self.get_report_view()}]
        
        if self.state == State.AWAITING_BLOCK_CONSENT:
            if message.content == 'y':
                self.state = State.REPORT_COMPLETE
                return [{"response": "The user has been blocked. They will no longer be able to contact you."}]
            elif message.content == 'n':
                self.state = State.REPORT_COMPLETE
                return [{"response": "The user will not be blocked."}]

        if self.state == State.AWAITING_SCAM_INFO:
            additional_message = ""
            if message.content != 'N/A':
                additional_message = "Thank you for this information. This will be passed to our content moderation team.\n"
            self.state = State.AWAITING_BLOCK_CONSENT
            return [{"response": f"{additional_message}{Report.BLOCK_USER_MESSAGE}"}]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

