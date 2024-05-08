from enum import Enum, auto
import discord
from discord.components import SelectOption
from discord.ui import Select, View
import re
from datetime import datetime

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    AWAITING_BLOCK_CONSENT = auto()
    AWAITING_ADDITIONAL_INFO = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    BLOCK_USER_MESSAGE = "Would you like to block the user from messaging you or viewing your profile in the future? (y/n)"
    NO_ADDITIONAL_INFO = "If no additional information can be provided, reply with N/A."

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_reason = None
        self.additional_info = None
        self.selections = []

    def get_report_view(self):
        options = [
            SelectOption(emoji="📫", label='Blackmail', value='Blackmail', description="You are being threatened to send cryptocurrency"),
            SelectOption(emoji="💰", label='Investment Scam', value='Investment Scam', description="You sent cryptocurrency to a fraudulent individual"),
            SelectOption(emoji="🔗", label='Suspicious Link', value='Suspicious Link', description="You received a link that may lead to a disreputable site"),
            SelectOption(emoji="⚠️", label="Imminent Danger", value="Imminent Danger", description="You are in immediate danger"),
            SelectOption(emoji="❓", label="Other", value="Other", description="You have a different reason for reporting")
        ]

        dropdown = Select(
            placeholder='Select the reason for reporting',
            options=options,
            custom_id='report_reason_dropdown'
        )

        async def callback(interaction):
            self.report_reason = dropdown.values[0]
            if dropdown.values[0] == 'Suspicious Link':
                self.state = State.AWAITING_ADDITIONAL_INFO
                await interaction.response.send_message(f"[Optional] Please provide additional details. This might include content of the website if then link was clicked (please do not click on the link if you have not done so already) or context regarding why the link was provided. {Report.NO_ADDITIONAL_INFO}")
            elif dropdown.values[0] == 'Blackmail':
                await interaction.response.send_message(f"Please select the form(s) of blackmail", view=self.get_blackmail_view())
            elif dropdown.values[0] == "Investment Scam":
                await interaction.response.send_message(f"Please select all that applies", view=self.get_scam_view())
            elif dropdown.values[0] == "Imminent Danger":
                self.state = State.AWAITING_ADDITIONAL_INFO
                await interaction.response.send_message(f"**If you are in a life-threatening situation, please contact your local authorities.**\n\n[Optional] Please provide additional details that might help our investigation. {Report.NO_ADDITIONAL_INFO}")
            else:
                self.state = State.AWAITING_ADDITIONAL_INFO
                await interaction.response.send_message("Please provide additional details for reporting.")

        dropdown.callback = callback
        view = View()
        view.add_item(dropdown)
        return view

    def get_scam_view(self):
        options = [
            SelectOption(emoji="💸", label='Assets Sent', value='Assets Sent', description="You have sent cryptocurrency"),
            SelectOption(emoji="🔒", label='Personal Information Provided' , value='Personal Information Provided', description="This might include bank info, account login"),
            SelectOption(emoji="🕵️‍♂️", label='Suspicion of Impersonation', value='Suspicion of Impersonation', description="You believe the account is fraudulent"),
        ]

        dropdown = Select(
            min_values=1,
            max_values=3,
            placeholder='Select all that applies',
            options=options,
            custom_id='scam_dropdown'
        )

        async def callback(interaction):
            self.selections = dropdown.values
            self.state = State.AWAITING_ADDITIONAL_INFO
            await interaction.response.send_message(f"[Optional] Please provide additional details to help our investigation. This might include date of transactions, specific information that was sent, or how much cryptocurrency was lost. {Report.NO_ADDITIONAL_INFO}")

        dropdown.callback = callback
        view = View()
        view.add_item(dropdown)
        return view

    def get_blackmail_view(self):
        options = [
            SelectOption(emoji="🔞", label='Reveal Explicit Content', value='Explicit Content', description="Threat to reveal your sexual/explicit content"),
            SelectOption(emoji="🔒", label='Reveal Personal/Sensitive Information', value='Personal/Sensitive Information', description="This could include addresses, SSN, account passwords"),
            SelectOption(emoji="👊", label='Threat to do Physical Harm', value='Threat to do Physical Harm', description="Threat to hurt yourself or others"),
        ]

        dropdown = Select(
            min_values=1,
            max_values=3,
            placeholder='Select form(s) of threat',
            options=options,
            custom_id='blackmail_dropdown'
        )

        async def callback(interaction):
            self.selections = dropdown.values
            self.state = State.AWAITING_ADDITIONAL_INFO
            await interaction.response.send_message(f"[Optional] Please provide additional details. {Report.NO_ADDITIONAL_INFO}")

        dropdown.callback = callback
        view = View()
        view.add_item(dropdown)
        return view

    def construct_report_summary(self, message):
        additional_information = f"\n* Additional Information: {self.additional_info}" if self.additional_info else ""
        reason_sub_category = f" - {', '.join(self.selections)}" if len(self.selections) > 0 else ""
        date = datetime.today().strftime("%B %d, %Y")
        return f"A report was filed on {date} by {message.author.name} on the following message: \n```{self.message.author.name}: {self.message.content}```\n* Report reason: {self.report_reason}{reason_sub_category}{additional_information} "

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
            self.message = message
            return [{"response": "I found this message:"},
                    {"response": "```" + message.author.name + ": " + message.content + "```"},
                    {"response": "\n\nPlease select the reason for reporting this message.", "view": self.get_report_view()}]
        
        if self.state == State.AWAITING_BLOCK_CONSENT:
            report_summary = self.construct_report_summary(message)
            if message.content == 'y':
                self.state = State.REPORT_COMPLETE
                response = f"{self.message.author.name} is no longer able to directly message you or view your profile."
            else:
                self.state = State.REPORT_COMPLETE
                response = f"{self.message.author.name} will still be able to directly message you and view your profile."

            return [{
                        "response": response, "summary": report_summary, "reported_message": self.message}]

        if self.state == State.AWAITING_ADDITIONAL_INFO:
            self.additional_info = message.content if message.content != 'N/A' else None
            if self.report_reason == 'Suspicious Link':
                response = "Thank you for reporting. Our content moderation team will review the link and flag it if necessary."
            elif self.report_reason == 'Blackmail' or self.report_reason == "Investment Scam":
                response = "Thank you for reporting. Our content moderation team will review the message and decide on an appropriate action. This may include removing the user from our platform."
            elif self.report_reason == 'Other':
                response = "Thank you for reporting. Our content moderation team will review the message and decide on an appropriate action."
            else:
                response = "Thank you for reporting. Our content moderation team will review the message and decide on an appropriate action. This may include working with the local authorities and providing message content."
            self.state = State.AWAITING_BLOCK_CONSENT
            return [{"response": response + f"\n\n{Report.BLOCK_USER_MESSAGE}"}]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

