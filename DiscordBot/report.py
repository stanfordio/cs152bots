from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    HATEFUL_CONDUCT_CONFIRMED = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORD = "yes"
    HATE_SPEECH_TYPES = ["slurs or symbols", "encouraging hateful behavior", "mocking trauma", "harmful stereotypes", "threatening violence"]
    SUBMIT_KEYWORD = "submit"
    CONTINUE_KEYWORD = "continue"

    HATE_SPEECH_KEYWORDS = []  # add keywords we want to use to detect hate speech here

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
        print(message)

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:

            # user confirmed that the message is hateful conduct
            if message.content == self.YES_KEYWORD:
                self.state == State.HATEFUL_CONDUCT_CONFIRMED
                reply = "Thank you for confirming that this is hateful conduct. "
                reply += "What kind of hateful conduct is it? "
                reply += "Please say one of the following:\n"
                slurs = "`slurs or symbols`: use of hateful slurs or symbols"
                behavior = "`encouraging hateful behavior`: encouraging other users to partake in hateful behavior"
                trauma = "`mocking trauma`: denying or mocking known hate crimes or events of genocide"
                stereotypes = "`harmful stereotypes`: perpetuating discrimination against protected characteristics such as race, ethnicity, national origin, religious affiliation, sexual orientation, sex, gender, gender identity, serios disease, disability, or immigration status"
                violence = "`threatening violence`: acts of credible threats of violence aimed at other users"
                types = [slurs, behavior, trauma, stereotypes, violence]
                reply += "\n".join(f"  • {type}" for type in types)
                self.state = State.AWAITING_MESSAGE
                return [reply]
            
            # user picked the relevant hate speech type
            if message.content in self.HATE_SPEECH_TYPES:
                # we need to add this message content to the final message that is submitted
                reply = "You have classified this message as " + message.content + ". "
                reply += "Would you like to submit your report now, or would you like to add more information? Please say `submit` if you would like to submit, or `continue` if you would like to add more information."
                self.state = State.AWAITING_MESSAGE
                return [reply]
            
            # user submits the report
            if message.content == self.SUBMIT_KEYWORD:
                self.report_complete()
                return ["Thank you for submitting your report. A moderator will review it shortly."]
            
            # user wants to add more information
            if message.content == self.CONTINUE_KEYWORD:
                # we need to add this message content to the final message that is submitted
                reply = "Tell us more about what you are reporting. Helpful information for us includes the date, time, and timezone of the message, as well as a detailed description of what the hateful conduct was and why it qualifies as the hateful conduct subtype that you classified it as. If applicable, we would also like to know the name of the channel in which the violation occurred, the username of the target of the conduct, and the name of the game."
                reply += "Please begin your response with `More information:`"
                self.state = State.AWAITING_MESSAGE
                return [reply]
            
            # user has added more information and now wants to submit
            if message.content.startswith("More information:"):
                reply = "Thank you for adding more information. Are you ready to submit? Please say `submit` to submit your report."
                self.state = State.AWAITING_MESSAGE
                return [reply]

            # add parsing for reporting a user

            # add parsing for reporting a Twitch channel

            # parse out the three ID strings from the message link
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
            reply = "I found this message: " + message.author.name + ": " + message.content + "\n"
            reply += "Is this hateful conduct? Please say `yes` or `no`."
            self.state = State.AWAITING_MESSAGE
            return [reply]

        
        if self.state == State.MESSAGE_IDENTIFIED:
            return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        self.state == State.REPORT_COMPLETE

    def get_report(self): 
        return self.message
    


    

