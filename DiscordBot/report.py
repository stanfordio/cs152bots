from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

    # Abuse Types
    SPAM = auto()
    OFFENSIVE_CONTENT = auto()
    NUDITY = auto()
    FRAUD = auto()
    MISINFORMATION = auto()
    HATE_HARASSMENT = auto()
    CSAM = auto()
    INTELLECTUAL = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    REPORTING_OPTIONS = ["1", "2", "3", "4", "5", "6", "7", "8"]

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
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
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            reply = "I found this message:" + "```" + message.author.name + ": " + message.content + "```" + "\n\n"
            reply += "Why are you reporting this message? Please select the number corresponding to the appropriate category.\n"
            reply += "1. Spam.\n"
            reply += "2. Offensive content.\n"
            reply += "3. Nudity and sexual content.\n"
            reply += "4. Fraud or scam.\n"
            reply += "5. Misinformation.\n"
            reply += "6. Hate and harassment.\n"
            reply += "7. Child sexual abuse material.\n"
            reply += "8. Intellectual property theft.\n"
            return [reply]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content not in self.REPORTING_OPTIONS:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            self.classify_report(message)

        return []
    

    def classify_report(self, message):
        if message.content == "1":
            self.state = State.SPAM
        elif message.content == "2":
            self.state = State.OFFENSIVE_CONTENT
        elif message.content == "3":
            self.state = State.NUDITY
        elif message.content == "4":
            self.state = State.FRAUD
        elif message.content == "5":
            self.state = State.MISINFORMATION
        elif message.content == "6":
            self.state = State.HATE_HARASSMENT
        elif message.content == "7":
            self.state = State.CSAM
        else:
            self.state = State.INTELLECTUAL


    def is_report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

