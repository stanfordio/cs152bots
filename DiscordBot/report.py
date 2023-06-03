from enum import Enum, auto
import discord
import re

class BotReactMessage(Enum):
    FIRST_LEVEL = auto()
    FRAUD_LEVEL = auto()
    MONEY_LEVEL = auto()
    BLOCK_LEVEL = auto()
    OTHER_THREAD = auto()

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    REPORT_CANCELED = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    DONE_KEYWORD = "done"

    FRAUD = "Fraud"
    SPAM = "Spam"
    HARASSMENT = "Harassment"
    IMPERSONATION = "Impersonation"
    FALSE_INFO = "False Information"
    REQUESTED_MONEY = "Requested Money"
    OBTAINED_MONEY = "Obtained Money"
    THREAT = "Threat"
    OTHER = "Other"
    NOT_INTERESTED = "Im Not Interetsed"
    IMMINENT_DANGER = "Imminent Danger"


    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.reported_user_id = None
        self.reporting_message_ids = {} # Map from id of message requiring react to type of request
        self.reported_issues = []
        self.reported_msg = None
    
    #TODO: Handle replies to the please elaborate message 
    # (just ID if its a reply to a message with the OTHER_THREAD id from self.reporting_message_ids)
    # And add message text to self.reported_issues

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
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            reply =  "Please react with one or more of the following to specify a reason for this report. Say `done` when done. Say `cancel` to cancel.\n"
            reply += ":one: : I suspect this user of fraud\n\n"
            reply += ":two: : This message contains spam\n\n"
            reply += ":three: : This message contains harassment\n\n"
            reply += ":four: : This user poses an imminent threat to my safety or the safety of others\n\n"
            reply += ":five: : I am no longer interested in this user"            
            self.reported_user_id = message.author.id
            self.reported_msg = message.content
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```" + reply]

        if self.state == State.MESSAGE_IDENTIFIED and message.content == self.DONE_KEYWORD:
            reply = "Thank you for reporting. "
            reply += "Our moderation team will review the profile and/or interaction and decide on appropriate action. "
            reply += "This may include profile warning, suspension, or removal for the reported party. "
            reply += "We will follow up with the status of the report within 72 hours.\n\n"
            reply += "Would you like to block this user to prevent them from sending you more messages in the future? "
            reply += "Please react with one of the following:\n"
            reply += ":one: : Yes, please block this person\n\n"
            reply += ":two: : No, don't block this person"
            self.state = State.REPORT_COMPLETE
            return [reply]
        #if self.state == State.MESSAGE_IDENTIFIED:
            # We have received a report but haven't finished the reporting flow and the user sends a new message
            #return ["It appears you are in the middle of reporting a message. Please complete or cancel the previous report before reporting a new message"]

    async def handle_react(self, payload):
        # only respond if we have a message identified
        self.reporting_user_id = payload.user_id
        if self.state == State.MESSAGE_IDENTIFIED:
            message_id = payload.message_id
            level = self.reporting_message_ids[message_id]
            emoji = payload.emoji
            if level == None:  
                #we shouldn't hit this
                return None
            if level == BotReactMessage.FIRST_LEVEL:
                if str(emoji.name) == '1️⃣':
                    reply = "You reported fraud. Please react with one or more of the following and say `done` when done:\n"
                    reply += ":one: : I suspect this person is impersonating someone else\n\n"
                    reply += ":two: : I suspect this person is lying about something on their profile\n\n" 
                    reply += ":three: : This person has asked me for money\n\n"
                    reply += ":four: : Other"
                elif str(emoji.name) == '2️⃣':
                    reply = None #"You reported spam. Thank you for reporting"
                    self.reported_issues.append(self.SPAM)
                elif str(emoji.name) == '3️⃣':
                    reply = None #"You reported harassment. Thank you for reporting"
                    self.reported_issues.append(self.HARASSMENT)
                elif str(emoji.name) == '4️⃣':
                    reply = None #"You reported an imminent threat. Thank you for reporting"
                    self.reported_issues.append(self.THREAT)
                elif str(emoji.name) == '5️⃣':
                    reply = None #"You reported you are no longer interested in this user. Thank you for reporting"
                else:
                    reply = None
            elif level == BotReactMessage.FRAUD_LEVEL:
                if str(emoji.name) == '1️⃣': 
                    reply = None #"You reported this person is impersonating someone else\n\n"
                    self.reported_issues.append(self.IMPERSONATION)
                elif str(emoji.name) == '2️⃣': 
                    reply = None #"You reported this person lying about something on their profile\n\n" 
                    self.reported_issues.append(self.FALSE_INFO)
                elif str(emoji.name) == '3️⃣': 
                    reply = "You reported his person has asked you for money. Please react with one of the follwing:\n\n"
                    reply += ":one: : I gave this person money\n\n"
                    reply += ":two: : I did not give this person money"
                    self.reported_issues.append(self.REQUESTED_MONEY)
                elif str(emoji.name) == '4️⃣': 
                    reply = "You selected other. Please elaborate by replying in thread to this message"
                else:
                    reply = None
            elif level == BotReactMessage.MONEY_LEVEL:
                if str(emoji.name) == '1️⃣': 
                    reply = "You reported money lost. Say done if you have no more to report, or continue reacting to the first message.\n\n"
                    self.reported_issues.append(self.OBTAINED_MONEY)
                elif str(emoji.name) == '2️⃣': 
                    reply = "You reported no money lost. Say done if you have no more to report, or continue reacting to the first message." 
                else:
                    reply = None
                #match emoji:
            elif level == BotReactMessage.BLOCK_LEVEL:
                if str(emoji.name) == '1️⃣': 
                    reply = "Thank you, we have blocked this user on your behalf\n\n"
                elif str(emoji.name) == '2️⃣': 
                    reply = "Thank you, no further action is required."
                else:
                    reply = None
                self.state = State.REPORT_COMPLETE
            else:
                reply = None
            return [reply]
        return [None]
            

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def report_canceled(self):
        return self.state == State.REPORT_CANCELED

    def get_reported_issues(self):
        return self.reported_issues

    def get_reported_message(self):
        return self.reported_msg

