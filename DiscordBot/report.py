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
    NO_KEYWORD = "no"
    HATE_SPEECH_TYPES = ["slurs or symbols", "encouraging hateful behavior", "mocking trauma", "harmful stereotypes", "threatening violence", "other"]
    SUBMIT_KEYWORD = "submit"
    CONTINUE_KEYWORD = "continue"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reported_message = None
        self.current_step = 0
    
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
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            if message.content == self.START_KEYWORD:
                self.state = State.REPORT_START
                        
            # step 0: user reports something as hateful conduct
            if self.current_step == 0:
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

                # we've found the message
                self.state = State.MESSAGE_IDENTIFIED
                self.reported_message = message
                reply = "I found this message: " + message.author.name + ": " + message.content + "\n"
                reply += "Is this hateful conduct? Please say `yes` or `no`."
                self.state = State.AWAITING_MESSAGE
                self.current_step = 1
                return [reply]
            
            # step 1: user confirmed that the message is hateful conduct, now needs to classify it
            if self.current_step == 1:
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
                    other = "`other`: the conduct does not fit into any of the above categories"
                    types = [slurs, behavior, trauma, stereotypes, violence, other]
                    reply += "\n".join(f"  • {type}" for type in types)
                    self.state = State.AWAITING_MESSAGE
                    self.current_step = 2
                    return [reply]
                if message.content == self.NO_KEYWORD:
                    reply = "This bot only accepts reports of hateful conduct. Please say `yes` if you would like to report hateful conduct, or `cancel` to cancel."
                    self.state = State.AWAITING_MESSAGE
                    return [reply]
                else:
                    reply = "Please say `yes` or `no`. If you would like to cancel your report, say `cancel`."
                    self.state = State.AWAITING_MESSAGE
                    return [reply]
                
            # step 2: user picked the relevant hate speech type, now decides whether to submit or continue
            if self.current_step == 2:
                if message.content in self.HATE_SPEECH_TYPES:
                    # we need to add this message content to the final message that is submitted
                    reply = "You have classified this message as " + message.content + ". "
                    if message.content == "threatening violence":
                        reply = "Since `threatening violence` could pose a real-world danger, we will mute the account of the user who sent this message for 1-3 days as we review your report."
                    reply += " Would you like to submit your report now, or would you like to add more information? Please say `submit` if you would like to submit, or `continue` if you would like to add more information."
                    self.state = State.AWAITING_MESSAGE
                    self.current_step = 3
                    return [reply]
                else:
                    reply = "That is not a valid hateful conduct subtype. Please choose one of the following:\n"
                    reply += "\n".join(f"  • `{type}`" for type in self.HATE_SPEECH_TYPES)
                    self.state = State.AWAITING_MESSAGE
                    return [reply]
                
            # step 3: user wants to add more information, now needs to add it
            if self.current_step == 3:
                if message.content == self.CONTINUE_KEYWORD:
                    # we need to add this message content to the final message that is submitted
                    reply = "Tell us more about what you are reporting. Helpful information for us includes the date, time, and timezone of the message, as well as a detailed description of what the hateful conduct was and why it qualifies as the hateful conduct subtype that you classified it as. If applicable, we would also like to know the username of the target of the conduct."
                    reply += " Please begin your response with the phrase, `More information:`"
                    self.state = State.AWAITING_MESSAGE
                    self.current_step = 4
                    return [reply]
                else:
                    reply = "Please say `submit` to submit, `continue` to add more information, or `cancel` to cancel your report."
                    self.state = State.AWAITING_MESSAGE
                    return [reply]
            
            # step 4: user has added more information, now wants to submit
            if self.current_step == 4:
                if message.content.startswith("more information:"):
                    reply = "Thank you for adding more information. Are you ready to submit? Please say `submit` to submit your report."
                    self.state = State.AWAITING_MESSAGE
                    self.current_step = 5
                    return [reply]
                else:
                    reply = "Please begin your response with `More information:`"
                    self.state = State.AWAITING_MESSAGE
                    return [reply]
            
            # user submits the report
            if message.content == self.SUBMIT_KEYWORD:
                self.report_complete()
                reply = "Thank you for submitting your report. We will follow up with you in 1-3 business days. In a live chat-based context, this may include muting or banning the user account, or removing the comment."
                reply += "If you would like to block the user who sent that message, please paste their username here. Otherwise, say `no`."
                self.state = State.AWAITING_MESSAGE
                self.current_step = 5
                return [reply]

            # step 5: user has opportunity to block the user
            if self.current_step == 5:
                if message.content == self.NO_KEYWORD:
                    return ["Okay. Thank you for your report."]
                else:
                    # block the user
                    return ["You have blocked user `" + message.content + "`. Thank you for your report."]

        return []

    def report_complete(self):
        self.state == State.REPORT_COMPLETE

    def get_report(self): 
        return self.message
    


    

