from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    SELECT_TYPE = auto()
    SUB_TYPE = auto()
    REPORT_SUBMITTED = auto()
    ASK_BLOCK_USER = auto()
    FINAL_MESSAGE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_type = None
        self.sub_type = None

    async def handle_message(self, message):
        '''
        This function manages the state transitions and user interactions for the reporting process in a Discord bot.
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.FINAL_MESSAGE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. Say `help` at any time for more information.\n\n"
            reply += "Please copy and paste the link to the message you want to report."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["Invalid link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I'm not in the reported guild. Please add me and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["Channel not found. Please try again or say `cancel` to cancel."]
            try:
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["Message not found. Please try again or say `cancel` to cancel."]
            
            self.state = State.SELECT_TYPE
            return ["Message found:", f"```{self.message.author.name}: {self.message.content}```",
                    "Please select the type of issue:",
                    "1. Harassment  2. Offensive Content  3. Spam  4. Imminent Danger"]

        if self.state == State.SELECT_TYPE:
            if message.content.isdigit() and 1 <= int(message.content) <= 4:
                self.report_type = int(message.content)
                reply = ["Please specify:"]
                if self.report_type == 1:
                    reply.append("1. Bullying  2. Stalking  3. Doxxing  4. Backlash")
                elif self.report_type == 2:
                    reply.append("1. Hate speech  2. Sexually explicit content  3. Child abuse  4. Extremist content")
                elif self.report_type == 3:
                    reply.append("1. Misinformation  2. Fraud/Extortion  3. Impersonation")
                elif self.report_type == 4:
                    reply.append("1. Credible threat  2. Violence  3. Self harm")
                self.state = State.SUB_TYPE
                return reply
            else:
                return ["Invalid selection. Please try again."]
        
        if self.state == State.SUB_TYPE:
            if message.content.isdigit() and 1 <= int(message.content) <= 4:
                self.sub_type = int(message.content)
                self.state = State.REPORT_SUBMITTED
                response = ["Thank you for reporting this message."]
                if self.report_type == 4:  # Imminent Danger
                    response.append("Our content moderation team will review this message and take the appropriate actions moving forward. This may include contacting law enforcement and removing the user from our platform.")
                else:
                    response.append("Our content moderation team will review this message and take the appropriate actions, which may include removing this user from our platform.")
                response.append("Would you like to block this user? This will prevent them from sending you messages in the future.")
                self.state = State.ASK_BLOCK_USER
                return response
            else:
                return ["Invalid subtype selected. Please try again or say `cancel` to cancel."]
        
        if self.state == State.ASK_BLOCK_USER:
            # Logic to handle user's choice about blocking could be implemented here.
            self.state = State.FINAL_MESSAGE
            return ["Thanks for your response. We'll take it from here!"]

        if self.state == State.FINAL_MESSAGE:
            return ["Thank you!"]
        
        return []

    def report_complete(self):
        return self.state == State.FINAL_MESSAGE
