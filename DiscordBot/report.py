from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_REASON = auto()
    AWAITING_SUBREASON = auto()
    ADDING_CONTEXT = auto()
    CHOOSE_BLOCK = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    REASONS = ["Harassment", "Offensive Content", "Spam", "Imminent Danger"]
    NON_FOCUS_REASONS = ["Offensive Content", "Spam", "Imminent Danger"]
    SUB_REASONS = {
        "Harassment": ["Doxxing", "Cyberstalking", "Threats", "Hate Speech", "Sexual Harassment", "Bullying", "Extortion", "Other"],
        "Offensive Content": ["Child Sexual Abuse Material", "Adult Sexually Explicit Content", "Violence", "Hate Speech", "Copyright Infringement"],
        "Spam": ["Impersonation", "Solicitation", "Malware"],
        "Imminent Danger": ["Violence to Others", "Self-Harm"]
    }
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reason = None
        self.sub_reason = None
        self.flagged_messages = []
    
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
                self.flagged_messages.append(message)
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if self.reason == None:
                self.state = State.AWAITING_REASON
                return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select the reason for reporting this message: Harassment, Offensive Content, Spam, Imminent Danger"]
            else:
                self.state = State.ADDING_CONTEXT
                message_count = len(self.flagged_messages)
                return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                        f"Would you like to add further context with relevant chat messages? You have currently submitted {message_count} message(s). Yes or No"]

        if self.state == State.AWAITING_REASON:
            if message.content not in self.REASONS:
                return ["Please select a valid reason for reporting: Harassment, Offensive Content, Spam, Imminent Danger"]
            else:
                self.reason = message.content
                self.state = State.AWAITING_SUBREASON
                if message.content == "Harassment":
                    return ["Please select the type of Harassment: Doxxing, Cyberstalking, Threats, Hate Speech, Sexual Harrasement, Bullying, Extortion, or Other"]
                if message.content == "Offensive Content":
                    return ["Please select the type of Offensive Content: Child Sexual Abuse Material, Adult Sexually Explicit Content, Violence, Hate Speech, or Copyright Infringement"]
                if message.content == "Spam":
                    return ["Please select the type of Spam: Impersonation, Solicitation, or Malware"]
                if message.content == "Imminent Danger":
                    return ["Please select the type of Danger: Violence to Others or Self-Harm"]

        if self.state == State.AWAITING_SUBREASON:
            if message.content not in self.SUB_REASONS[self.reason]:
                return [f"Please select a valid type of {self.reason}: {', '.join(self.SUB_REASONS[self.reason])}"]
            else:
                self.sub_reason = message.content
                if self.reason in self.NON_FOCUS_REASONS:
                    self.state = State.CHOOSE_BLOCK
                    return ["Thank you for reporting. Our content moderation team will review the report and decide on appropriate action. Would you like to block the offending user(s)? Yes or No"]
                else:
                    self.state = State.ADDING_CONTEXT
                    return ["Would you like to add further context or select relevant chat messages? Yes or No"]
        
        if self.state == State.ADDING_CONTEXT:
            if message.content not in ["Yes", "No"]:
                return ["Would you like to add further context with relevant chat messages? Yes or No"]
            else:
                if message.content == "Yes":
                    self.state = State.AWAITING_MESSAGE
                    return ["Please provide the links of the relevant chat messages you want to add."]
                else:
                    self.state = State.CHOOSE_BLOCK
                    return ["Thank you for reporting. Our content moderation team will review the report and decide on appropriate action. Would you like to block the offending user(s)? Yes or No"]
        
        if self.state == State.CHOOSE_BLOCK:
            if message.content not in ["Yes", "No"]:
                return ["Thank you for reporting. Our content moderation team will review the report and decide on appropriate action. Would you like to block the offending user(s)? Yes or No"]
            else:
                self.state = State. REPORT_COMPLETE
                reply = f"Your report has been submitted for review.\n Reason: {self.reason}.\n Subreason: {self.sub_reason}.\n"
                if message.content == "Yes":
                    authors = self.get_authors()
                    reply += f"The offending authors of the flagged messages have been blocked:\n{authors}"
            return [reply]
    
    def get_authors(self):
        authors = [msg.author.name for msg in self.flagged_messages]
        unique_authors = list(set(authors))
        return "\n".join(unique_authors)


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

