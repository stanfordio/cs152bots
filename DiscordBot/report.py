from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()

    SELECT_REASON = auto()
    SCAM_TYPE = auto()
    SOLICITATION_TYPE = auto()
    INVOLVES_CRYPTO = auto()
    AWAITING_ALT_REASON = auto()
    
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

        # self.selected_reason = None
        # self.selected_scam_type = None
        # self.selected_solicitation_type = None
        # self.selected_involves_crypto = None
    
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
            reply =  "Thank you for starting the reporting process. "
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
                self.message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            # self.state = State.MESSAGE_IDENTIFIED
            # return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #         "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]

            self.state = State.SELECT_REASON
            return [
                "I found this message:",
                f"```{self.message.author.name}: {self.message.content}```",
                "Please select the reason for reporting this user.",
                "Options: Spam, Hatespeech, Fraud/Scam, Offensive Content, Other"
            ]

        if self.state == State.SELECT_REASON:
            reason = message.content.strip().lower()
            if reason in ["spam", "hatespeech", "offensive content"]:
                self.state = State.REPORT_COMPLETE
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user."]
            elif reason == "fraud/scam":
                self.state = State.SCAM_TYPE
                return ["Please select a type of scam: Solicitation, Impersonation, Other"]
            elif reason == "other":
                self.state = State.AWAITING_ALT_REASON
                return ["Please specify the reason for reporting:"]
            else:
                return ["Invalid option, please select a reason for reporting from: Spam, Hatespeech, Fraud/Scam, Offensive Content, Other"]

        if self.state == State.SCAM_TYPE:
            scam_type = message.content.strip().lower()
            if scam_type == "solicitation":
                self.state = State.SOLICITATION_TYPE
                return ["Please select the type of solicitation: Job Opportunity, Investment Opportunity, Networking Event"]
            elif scam_type == "impersonation":
                self.state = State.REPORT_COMPLETE
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user."]
            elif scam_type == "other":
                self.state = State.AWAITING_ALT_REASON
                return ["Please specify the reason for reporting:"]
            else:
                return ["Invalid option, please select a type of scam from: Solicitation, Impersonation, Other"]

        if self.state == State.SOLICITATION_TYPE:
            solicitation_type = message.content.strip().lower()
            if solicitation_type in ["job opportunity", "networking event"]:
                self.state = State.REPORT_COMPLETE
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user."]
            elif solicitation_type == "investment opportunity":
                self.state = State.INVOLVES_CRYPTO
                return ["Does this involve cryptocurrency? (Yes/No)"]
            else:
                return ["Invalid option, please select a type of solicitation from: Job opportunity, Investment opportunity, Networking event"]

        if self.state == State.INVOLVES_CRYPTO:
            response = message.content.strip().lower()
            if response == "yes":
                self.state = State.REPORT_COMPLETE
                return [f"Thanks for notifying us. We have blocked the reported user {self.message.author.name}."]
            elif response == "no":
                self.state = State.REPORT_COMPLETE
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user."]
            else:
                return ["Invalid response, please type 'Yes' or 'No'."]

        if self.state == State.AWAITING_ALT_REASON:
            self.state = State.REPORT_COMPLETE
            return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user."]
        
        # if self.state == State.MESSAGE_IDENTIFIED:
        #     return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

