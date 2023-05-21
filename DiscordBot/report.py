from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.CSAM_stage = 0
        self.age_stage = 0
        self.block_stage = 0
        self.stage = 0
        self.report_type = None
        self.abuse_report = None
        self.client = client
        self.message = None

    def handle_flow(self, message):
        '''
        This function defines the flow of the reporting process. It is called when the user has identified the message they want to report.
        '''

        types = {
            "1": "Violence",
            "2": "Harassment",
            "3": "Copyright Infringment",
            "4": "Spam",
            "5": "Sensitive or Offensive Content",
            "6": "Other"
        }
        if (self.stage == 0):
            self.message = message
            self.stage = 1
            reply = "Please select a reason for your report by typing the corresponding number:\n"
            reply += "1. Violence\n"
            reply += "2. Harassment\n"
            reply += "3. Copyright Infringment\n"
            reply += "4. Spam\n"
            reply += "5. Sensitive or Offensive Content\n"
            reply += "6. Other\n"
            return [reply]
        if (self.stage == 1):
            
            replies = {
                "1": "Please select the type of violence you are reporting by typing the corresponding number:\n1. Graphic Descriptions of Violence\n2. Threats of Violence\n3. Self-Harm\n4. Other",
                "2": "Please select the type of harassment you are reporting by typing the corresponding number:\n1. Hate Speech\n2. Bullying\n3. Unwanted Contact\n4. Revealing personal information\n5. Other",
                "3": "Thank you for reporting this message. Please provide any additional information you think is relevant.",
                "4": "Please select the type of spam you are reporting by typing the corresponding number:\n1. Fraud / Scam\n2. Impersonation\n3. Phishing",
                "5": "Please select the type of sensitive or offensive content you are reporting by typing the corresponding number:\n1. Sexually Explicit Content\n2. Hate Speech\n3. Child Sexual Abuse Materials\n4. Other",
                "6": "Thank you for reporting this message. Please provide any additional information you think is relevant."
            }
            reply = replies[message.content] if message.content in replies else "Invalid input. Please try again."
            if (message.content in replies):
                self.stage = 2
                self.report_type = types[message.content]
                self.abuse_report.append += "Report Type: " + self.report_type + "\n"
            return [reply]
        if (self.stage == 2):
            if (self.report_type == "Violence"):
                self.state = State.REPORT_COMPLETE
                self.stage = 3
                return ["Thank you for reporting this content. Our moderation team will review and decide on an appropriate course of action, which could involve notifying local authorities."]
            if (self.report_type == "Harassment" and message.content == "3"):
                self.stage = 4
                return self.age_verification_action(message)
            if (self.report_type == "Sensitive or Offensive Content" and message.content == "3"):
                self.stage = 5
                return self.CSAM_action(message)
            if (["1", "2", "4", "5", "6"].__contains__(message.content)):
                self.stage = 6
                return self.block_action(message)
            else:
                return ["Invalid input. Please try again."]
        if (self.stage == 3):
            if (message.content == "confirm"):
                self.stage = 0
                self.state = State.REPORT_COMPLETE
                return ["Report sent!"]
            else:
                self.stage = 0
                self.state = State.REPORT_COMPLETE
                return ["Report cancelled."]
        if (self.stage == 4):
            return self.age_verification_action(message)      
        if (self.stage == 5):
            return self.CSAM_action(message)
        if (self.stage == 6):
            return self.block_action(message)
            
    def age_verification_action(self, message):
        if (self.age_stage == 0):
            self.age_stage = 1
            return ["Are you over 18?\n1. Yes\n2. No"]
        if (self.age_stage == 1):
            if (message.content == "1"):
                self.age_stage = 2
                return ["1. The user is trying to get close to me, asking me personal information, or showing signs of “grooming,” asking me for sexual material.\n2. Does not apply"]
            elif (message.content == "2"):
                self.age_stage = 0
                self.stage = 6
                return self.block_action(message)
            else:
                return ["Invalid input. Please try again."]
        if (self.age_stage == 2):
            if (message.content == "1"):
                reply = "Here are some resources with information about grooming. We highly encourage you to keep yourself informed about these behaviors as you continue to interact with this user."
            #TODO: store info from message and add resources
            self.age_stage = 0
            self.stage = 6
            return self.block_action(message)
        else:
            return ["Invalid input. Please try again."]

    def CSAM_action(self, message):
        if (self.CSAM_stage == 0):
            self.CSAM_stage = 1
            return ["What type of material?\n1. Images or Videos\n2. External Links\n3. Other"]
        if (self.CSAM_stage == 1):
            if (message.content == "1"):
                self.CSAM_stage = 2
                return ["Please provide a description of the material."]
            elif (message.content == "2"):
                self.CSAM_stage = 2
                return ["Please provide a description of the material."]
            elif (message.content == "3"):
                self.CSAM_stage = 2
                return ["Please provide a description of the material."]
            else:
                return ["Invalid input. Please try again."]
        if (self.CSAM_stage == 2):
            print(message.content)
            self.CSAM_stage = 0
            self.stage = 6
            return self.block_action(message)
        else:
            return ["Invalid input. Please try again."]

    def block_action(self, message):
        if (self.block_stage == 0):
            self.block_stage = 1
            return ["Would you like to block the user?\n1. Yes\n2. No"]
        if (self.block_stage == 1):
            reply = "Thank you for reporting this content. Our moderation team will review and decide on an appropriate course of action, which could include post/content removal, a warning, account removal, or even notifying local authorities if necessary.\n\n"
            if (message.content == "1"):
                #TODO: Store info from message 
                print("todo: store info from message")
                self.block_stage = 0
                self.stage = 0
                self.state = State.REPORT_COMPLETE
                return [reply]
            if (message.content == "2"):
                self.block_stage = 0
                self.stage = 0
                self.state = State.REPORT_COMPLETE
                return [reply]
            else:
                return ["Invalid input. Please try again."]
    
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
            return self.handle_flow(message)
        
        if self.state == State.MESSAGE_IDENTIFIED:
            return self.handle_flow(message)

        return []
    
    

    async def handle_mod_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START: 
            reply = "Is this content CSAM? Please reply 'yes' or 'no'."
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
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
        
        
        if self.state == State.MESSAGE_IDENTIFIED:
            return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
class ModReport:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
    async def handle_mod_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START: 
            reply = "Is this content CSAM? Please reply 'yes' or 'no'."
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
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
        
        
        if self.state == State.MESSAGE_IDENTIFIED:
            return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
      

