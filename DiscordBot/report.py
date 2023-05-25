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
    REPORT_CANCELED = auto()
    REPORT_FILED = auto()

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
    NUM_TO_IND = {
        "1️⃣": 0, 
        "2️⃣": 1, 
        "3️⃣": 2, 
        "4️⃣": 3, 
        "5️⃣": 4, 
        "6️⃣": 5, 
        "7️⃣": 6, 
        "8️⃣": 7, 
        "9️⃣": 8
    }

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reason = None
        self.sub_reason = None
        self.reaction_mode = False
        self.flagged_messages = []
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_CANCELED
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
                self.reaction_mode = True
                return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select the reason for reporting this message:\n1️⃣: Harassment\n2️⃣: Offensive Content\n3️⃣: Spam\n4️⃣: Imminent Danger"]
            else:
                self.state = State.ADDING_CONTEXT
                message_count = len(self.flagged_messages)
                return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                        f"Would you like to add further context with relevant chat messages? You have currently submitted {message_count} message(s). Yes or No"]

        if self.state == State.AWAITING_REASON:
            if self.reason == None:
                return ["Please select the reaction corresponding to your valid reason for reporting."]
            else:
                self.reaction_mode = True
                self.state = State.AWAITING_SUBREASON
                if self.reason == "Harassment":
                    return ["Please select the type of Harassment:\n1️⃣: Doxxing\n2️⃣: Cyberstalking\n3️⃣: Threats\n4️⃣: Hate Speech\n5️⃣: Sexual Harrasement\n6️⃣: Bullying\n7️⃣: Extortion\n8️⃣: Other"]
                if self.reason == "Offensive Content":
                    return ["Please select the type of Offensive Content:\n1️⃣: Child Sexual Abuse Material\n2️⃣: Adult Sexually Explicit Content\n3️⃣: Violence\n4️⃣: Hate Speech\n5️⃣: Copyright Infringement"]
                if self.reason == "Spam":
                    return ["Please select the type of Spam:\n1️⃣: Impersonation\n2️⃣: Solicitation\n3️⃣: Malware"]
                if self.reason == "Imminent Danger":
                    return ["Please select the type of Danger:\n1️⃣: Violence to Others\n2️⃣: Self-Harm"]

        if self.state == State.AWAITING_SUBREASON:
            if self.sub_reason == None:
                return ["Please select the reaction corresponding to your subreason."]
            else:
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
                self.state = State. REPORT_FILED
                reply = f"Your report has been submitted for review.\n Reason: {self.reason}.\n Subreason: {self.sub_reason}.\n"
                if message.content == "Yes":
                    authors = self.get_authors()
                    reply += f"The offending authors of the flagged messages have been blocked:\n{authors}"
            return [reply]

    async def handle_reaction(self, reaction):
        self.reaction_mode = False
        if self.state == State.AWAITING_REASON:
            self.reason = self.REASONS[self.NUM_TO_IND[reaction.emoji]] 
            return["You selected " + self.reason + " as your reason.",  "Type anything to continue."]
        if self.state == State.AWAITING_SUBREASON:
            self.sub_reason = self.SUB_REASONS[self.reason][self.NUM_TO_IND[reaction.emoji]]
            return["You selected " + self.sub_reason + " as your subreason.",  "Type anything to continue."]
        
    
    def get_authors(self):
        authors = [msg.author.name for msg in self.flagged_messages]
        unique_authors = list(set(authors))
        return "\n".join(unique_authors)

    def report_canceled(self):
        return self.state == State.REPORT_CANCELED

    def report_filed(self):
        return self.state == State.REPORT_FILED
    


    

