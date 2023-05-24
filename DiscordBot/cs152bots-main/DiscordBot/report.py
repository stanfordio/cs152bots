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
            self.reportedUser = message.author.name

            self.message = message

            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please classify the message as one of the following: ", \
                    "Use the command `spam` to classify the message as spam.", \
                    "Use the command `harassment` to classify the message as harassment.", \
                    "Use the command `offensive` to classify the message as being offensive.", \
                    "Use the command `harm` if the message threatens to cause harm.\n"]

        # Classifying the message.
        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content == self.SPAM:
                self.state = State.SPAM
                return ["You have classified the message as spam.", \
                        "Please identify if the spam is a fraud or an impersonation.", \
                        "Use the command `fraud` to classify the spam as fraudulent.", \
                        "Use the command `impersonation` to classify the spam as an impersonation.\n"]

            if message.content == self.HARASSMENT:
                self.state = State.HARASSMENT
                return ["You have classified the message as harassment.", \
                        "Please identify if the harassment is directed to you or someone else.", \
                        "Use the command `me` if the harasser is targeting you.", \
                        "Use the command `other` if the harasser is targeting someone else.\n"]

            if message.content == self.OFFENSIVE:
                self.state = State.OFFENSIVE_CONTENT
                return ["You have classified the message as offensive.", \
                        "Please identify under which category the offensive content falls under.", \
                        "Use the command `graphic` if the message contains graphic violence.", \
                        "Use the command `sexual` if the message contains sexually explicit content or nudity.", \
                        "Use the command `hate` if the message is a hate speech.\n"]

            if message.content == self.HARM:
                self.state = State.HARM_OR_DANGER
                return ["You have classified the message as harmful or dangerous.", \
                        "Please identify the type of harm the message insinuates", \
                        "Use the command `threatens` if the message threatens someone.", \
                        "Use the command `self` if the message is about self-harm or suicide.", \
                        "Use the command `substance` if the message is related to illegal substance abuse.\n"]

        # spam control flow
        if self.state == State.SPAM:
            if message.content == self.FRAUD:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message is a fraudulent spam.", \
                        "Report complete. Thank you very much."]

            if message.content == self.IMPERSONATION:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message is a spam where " + self.reportedUser + "impersonates as someone else.", \
                        "Report complete. Thank you very much."]

        # harassment control flow
        if self.state == State.HARASSMENT:
            if message.content == self.TARGETING_ME:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that this message is proof of harassment against you by " + self.reportedUser + ".", \
                        "Report complete. Thank you very much."]

            if message.content == self.TARGETING_OTHERS:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that this message is proof of harassment against someone else by " + self.reportedUser + ".", \
                        "Report complete. Thank you very much."]

        # offensive content control flow
        if self.state == State.OFFENSIVE_CONTENT:
            if message.content == self.GRAPHIC_VIOLENCE:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message contains grahpic violence.", \
                        "Report complete. Thank you very much."]

            if message.content == self.SEXUALLY_EXPLICIT_CONTENT or message.content == self.NUDITY:
                self.state = State.SEXUAL_CONTENT
                return ["You have specified that the message contains sexually explicit content.", \
                        "Please state if the sexual content features an adult or a child/minor.", \
                        "Use the command `adult` if the message features only adults.", \
                        "Use the command `child` if the message may feature a child or a minor."]

            if message.content == self.HATE_SPEECH:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message is a hate speech against someone else.", \
                        "Report complete. Thank you very much."]

        if self.state == State.SEXUAL_CONTENT:
            if message.content == self.ADULT:
                self.state = State.ADULT
                return ["Thank you for your report. We take these matters very seriously and will "
                        "investigate this message promptly. We will take appropriate actions, which "
                        "may include removal of the message and/or the user."]

            if message.content == self.CSAM:
                self.state = State.CSAM
                return ["Thank you for your report. We take these matters very seriously and will "
                        "investigate this message promptly. We will take appropriate actions, "
                        "which may include removal of the message and/or the user and working "
                        "with law enforcement."
                        ]

        # harm/danger control flow
        if self.state == State.HARM_OR_DANGER:
            if message.content == self.THREATENS_OTHERS:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message contains threats to someone else.", \
                        "Report complete. Thank you very much."]

            if message.content == self.SELF_HARM:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message contains elements of self harm or suicide", \
                        "Report complete. Thank you very much."]

            if message.content == self.SUBSTANCE_ABUSE:
                self.state = State.REPORT_COMPLETE
                return ["You have reported that the message is related to illegal substance abuse.", \
                        "Report complete. Thank you very much."]

        return []

    async def moderate(self, message):
        if self.state == State.ADULT:
            return [f"You are moderating the message `{message.content}`, which has been reported for adult nudity.", \
                     "Please state if the report is valid.", \
                     "Use the command `valid` if the message features adult nudity.", \
                     "Use the command `invalid` if the message does not actually feature adult nudity."]

        if self.state == State.CSAM:
            return [f"You are moderating the message `{message.content}`, which has been reported for CSAM.", \
                     "Please state if the report is valid.", \
                     "Use the command `valid` if the message features CSAM.", \
                     "Use the command `invalid` if the message does not actually feature CSAM."]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

