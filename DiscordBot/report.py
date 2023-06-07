from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

    # Message Classification
    SPAM = auto()
    HARASSMENT = auto()
    OFFENSIVE_CONTENT = auto()
    HARM_OR_DANGER = auto()

    # Offensive Content Classification
    SEXUAL_CONTENT = auto()

    # Sexual Content Classification
    ADULT = auto()
    CSAM = auto()

    # MODERATOR FLOW
    ADULT_UNDER_REVIEW = auto()
    CSAM_UNDER_REVIEW = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    QUEUE_KEYWORD = "queue"
    EXIT_KEYWORD = "exit"

    SPAM = "spam"
    HARASSMENT = "harassment"
    OFFENSIVE = "offensive"
    HARM = "harm"

    FRAUD = "fraud"
    IMPERSONATION = "impersonation"

    TARGETING_ME = "me"
    TARGETING_OTHERS = "other"

    GRAPHIC_VIOLENCE = "graphic"
    SEXUALLY_EXPLICIT_CONTENT = "sexual"
    NUDITY = "nuidity"
    HATE_SPEECH = "hate"

    THREATENS_OTHERS = "others"
    SELF_HARM = "self"
    SUBSTANCE_ABUSE = "substance"

    ADULT = "adult"
    CSAM = "child"

    BLOCK = "block"
    HIDE = "hide"
    NONE = "no"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reportedUser = None
        self.reporter = None
        self.link = None
    
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
            self.reporter = message.author.name
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            self.link = message.content

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
            self.reportedUser = message.author.name

            self.message = message

            reply = "I found this message: ```" + message.author.name + ": " + message.content + "```\n"
            reply += "Please classify the message as one of the following: \n"
            reply += "Use the command `spam` to classify the message as spam.\n"
            reply += "Use the command `harassment` to classify the message as harassment.\n"
            reply += "Use the command `offensive` to classify the message as containing offensive content or nudity.\n"
            reply += "Use the command `harm` if the message threatens to cause harm.\n"

            return [reply]

        # Classifying the message.
        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content == self.SPAM:
                self.state = State.SPAM
                reply = "You have classified the message as spam.\n"
                reply += "Please identify if the spam is a fraud or an impersonation.\n"
                reply += "Use the command `fraud` to classify the spam as fraudulent.\n"
                reply += "Use the command `impersonation` to classify the spam as an impersonation.\n"
                return [reply]

            if message.content == self.HARASSMENT:
                self.state = State.HARASSMENT
                reply = "You have classified the message as harassment.\n"
                reply += "Please identify if the harassment is directed to you or someone else.\n"
                reply += "Use the command `me` if the harasser is targeting you.\n"
                reply += "Use the command `other` if the harasser is targeting someone else.\n"
                return [reply]

            if message.content == self.OFFENSIVE:
                self.state = State.OFFENSIVE_CONTENT
                reply = "You have classified the message as offensive.\n"
                reply += "Please identify under which category the offensive content falls under.\n"
                reply += "Use the command `graphic` if the message contains graphic violence.\n"
                reply += "Use the command `sexual` if the message contains sexually explicit content or nudity.\n"
                reply += "Use the command `hate` if the message is a hate speech.\n"
                return [reply]

            if message.content == self.HARM:
                self.state = State.HARM_OR_DANGER
                reply = "You have classified the message as harmful or dangerous.\n"
                reply += "Please identify the type of harm the message insinuates\n"
                reply += "Use the command `threatens` if the message threatens someone.\n"
                reply += "Use the command `self` if the message is about self-harm or suicide.\n"
                reply += "Use the command `substance` if the message is related to illegal substance abuse.\n"
                return [reply]

        # spam control flow
        if self.state == State.SPAM:
            if message.content == self.FRAUD:
                self.state = State.REPORT_COMPLETE
                reply = "You have reported that the message is a fraudulent spam.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

            if message.content == self.IMPERSONATION:
                self.state = State.REPORT_COMPLETE
                reply = f"You have reported that the message is a spam where {self.reportedUser} impersonates as someone else.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

        # harassment control flow
        if self.state == State.HARASSMENT:
            if message.content == self.TARGETING_ME:
                self.state = State.REPORT_COMPLETE
                reply = f"You have reported that this message is proof of harassment against you by {self.reportedUser}.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

            if message.content == self.TARGETING_OTHERS:
                self.state = State.REPORT_COMPLETE
                reply = f"You have reported that this message is proof of harassment against someone else by {self.reportedUser}.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

        # offensive content control flow
        if self.state == State.OFFENSIVE_CONTENT:
            if message.content == self.GRAPHIC_VIOLENCE:
                self.state = State.REPORT_COMPLETE
                reply = "You have reported that the message contains grahpic violence.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

            if message.content == self.SEXUALLY_EXPLICIT_CONTENT or message.content == self.NUDITY:
                self.state = State.SEXUAL_CONTENT
                reply = "You have specified that the message contains sexually explicit content.\n"
                reply += "Please state if the sexual content features an adult or a child/minor.\n"
                reply += "Use the command `adult` if the message features only adults.\n"
                reply += "Use the command `child` if the message may feature a child or a minor.\n"
                return [reply]

            if message.content == self.HATE_SPEECH:
                self.state = State.REPORT_COMPLETE
                reply = "You have reported that the message is a hate speech against someone else.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

        if self.state == State.SEXUAL_CONTENT:
            if message.content == self.ADULT:
                self.state = State.ADULT
                reply = "Thank you for your report. We take these matters very seriously and will " \
                        "investigate this message promptly. We will take appropriate actions, which " \
                        "may include removal of the message and/or the user."
                return [reply]

            if message.content == self.CSAM:
                self.state = State.CSAM
                reply = "Thank you for your report. We take these matters very seriously and will " \
                        "investigate this message promptly. We will take appropriate actions, " \
                        "which may include removal of the message and/or the user and working " \
                        "with law enforcement.\n"
                return [reply]

        # harm/danger control flow
        if self.state == State.HARM_OR_DANGER:
            if message.content == self.THREATENS_OTHERS:
                self.state = State.REPORT_COMPLETE
                reply = "You have reported that the message contains threats to someone else.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

            if message.content == self.SELF_HARM:
                self.state = State.REPORT_COMPLETE
                reply = "You have reported that the message contains elements of self harm or suicide.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

            if message.content == self.SUBSTANCE_ABUSE:
                self.state = State.REPORT_COMPLETE
                reply = "You have reported that the message is related to illegal substance abuse.\n"
                reply += "Report complete. Thank you very much.\n"
                return [reply]

        return []

    async def moderate(self, message):
        if self.state == State.ADULT:
            reply = "You are moderating the message ```"
            reply += f" {message.content} "
            reply += "``` "
            reply += f"{self.link}, which has been reported for adult nudity."
            reply += "Please state if the report is valid.\n"
            reply += "Use the command `valid` if the message features adult nudity.\n"
            reply += "Use the command `invalid` if the message does not actually feature adult nudity.\n"
            reply += "Use the command `wrong-type` if the message features CSAM.\n"
            return [reply]

        if self.state == State.CSAM:
            reply = "You are moderating the message ```"
            reply += f" {message.content} "
            reply += "``` "
            reply += f"{self.link}, which has been reported for CSAM."
            reply += "Please state if the report is valid.\n"
            reply += "Use the command `valid` if the message features CSAM.\n"
            reply += "Use the command `invalid` if the message does not actually feature CSAM or nudity.\n"
            reply += "Use the command `wrong-type` if the message features nudity but is not CSAM.\n"
            return [reply]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def report_csam(self):
        return self.state == State.CSAM

    def report_adult(self):
        return self.state == State.ADULT