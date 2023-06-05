from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    REPORT_CANCELLED = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    TYPE_OF_CSAM_MATERIAL = {
        "1": "Images or Videos", 
        "2": "External links", 
        "3": "Other", 
    }

    BLOCK_ACTION = {
        "1": "Yes",
        "2": "No"
    }

    VIOLENCE_TYPES = {
        "1": "Graphic Descriptions of Violence", 
        "2": "Threats of Violence", 
        "3": "Self-harm", 
        "4": "Other"
    }

    HARRASSMENT_TYPES = {
        "1": "Hate Speech", 
        "2": "Bullying", 
        "3": "Unwanted Contact", 
        "4": "Revealing Personal Information",
        "5": "Other"
    }

    SPAM_TYPES = {
        "1": "Fraud / Scam", 
        "2": "Impersonation", 
        "3": "Phishing", 
    }

    EXPLICIT_CONTENT = {
        "1": "Sexually Explicit Content", 
        "2": "Hate Speech", 
        "3": "Child Sexual Abuse Material", 
        "4": "Other"
    }

    INVALID_MESSAGE = "Invalid input. Please try again."

    def __init__(self, client):
        self.state = State.REPORT_START
        self.CSAM_stage = 0
        self.age_stage = 0
        self.block_stage = 0
        self.stage = 0
        self.report_type = None
        self.abuse_report = ["\n\n!!!STARTING A NEW ABUSE REPORT !!!\n\n"]
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

        replies = {
            "1": "Please select the type of violence you are reporting by typing the corresponding number:\n1. Graphic Descriptions of Violence\n2. Threats of Violence\n3. Self-Harm\n4. Other",
            "2": "Please select the type of harassment you are reporting by typing the corresponding number:\n1. Hate Speech\n2. Bullying\n3. Unwanted Contact\n4. Revealing personal information\n5. Other",
            "3": "Thank you for reporting this message. Please provide any additional information you think is relevant.",
            "4": "Please select the type of spam you are reporting by typing the corresponding number:\n1. Fraud / Scam\n2. Impersonation\n3. Phishing",
            "5": "Please select the type of sensitive or offensive content you are reporting by typing the corresponding number:\n1. Sexually Explicit Content\n2. Hate Speech\n3. Child Sexual Abuse Materials\n4. Other",
            "6": "Thank you for reporting this message. Please provide any additional information you think is relevant."
        }

        print (self.stage, self.report_type, message.content)
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
            self.abuse_report += ["Reported Message: " + message.content + "\n"]
            self.abuse_report += ["Reported User: " + message.author.name + "\n"]
            self.abuse_report += ["Reported User ID: " + str(message.author.id) + "\n"]
            self.abuse_report += ["Reported Message Url: " + message.jump_url + "\n"]

            # self.abuse_report += [reply + "\n"]
            return [reply]
        if (self.stage == 1):
            
            reply = replies[message.content] if message.content in replies else "Invalid input. Please try again."
            if (message.content in replies):
                self.stage = 2
                self.report_type = types[message.content]
                self.abuse_report += ["Report Type: " + self.report_type + "\n"]
            # self.abuse_report += [reply + "\n"]
            return [reply]
        if (self.stage == 2):
            # self.abuse_report += ["Response: " + replies[message.content] + "\n"]
            if (self.report_type == "Violence"):
                if message.content not in self.VIOLENCE_TYPES:
                    return [self.INVALID_MESSAGE]
                self.abuse_report += [f'Subtype: {message.content} - {self.VIOLENCE_TYPES[message.content]}']
                if message.content == "4":
                    self.stage = 3
                    return [replies["6"]]
                self.state = State.REPORT_COMPLETE
                self.stage = 3
                return ["Thank you for reporting this content. Our moderation team will review and decide on an appropriate course of action, which could involve notifying local authorities."]
            if (self.report_type == "Harassment"):
                if message.content not in self.HARRASSMENT_TYPES:
                    return [self.INVALID_MESSAGE]
                self.abuse_report += [f'Subtype: {message.content} - {self.HARRASSMENT_TYPES[message.content]}\n']
                if message.content == "3":
                    self.stage = 4
                    return self.age_verification_action(message)
                if message.content == "5":
                    self.stage = 3
                    return [replies["6"]]
                self.stage = 6
                return self.block_action(message)
            if (self.report_type == "Copyright Infringment"):
                self.abuse_report += ["User Response: " + message.content + "\n"]
                self.stage = 6
                return self.block_action(message)
            if self.report_type == "Spam":
                if message.content not in self.SPAM_TYPES:
                    return [self.INVALID_MESSAGE]
                self.abuse_report += [f'Subtype: {message.content} - {self.SPAM_TYPES[message.content]}\n']
                self.stage = 6
                return self.block_action(message)
            if self.report_type == "Sensitive or Offensive Content":
                if message.content not in self.EXPLICIT_CONTENT:
                    return [self.INVALID_MESSAGE]
                self.abuse_report += [f'Subtype: {message.content} - {self.EXPLICIT_CONTENT[message.content]}\n']
                if message.content == "3":
                    self.stage = 5
                    return self.CSAM_action(message)
                if message.content == "4":
                    self.stage = 3
                    return [replies["6"]]
                self.stage = 6
                return self.block_action(message)
            if self.report_type == "Other":
                self.abuse_report += [f'User Response: {message.content}\n']
                self.state = State.REPORT_COMPLETE
                self.stage = 3
                return ["Thank you for reporting this content. Our moderation team will review and decide on an appropriate course of action, which could involve notifying local authorities."]
    
        # the stage for entering more info 
        if (self.stage == 3):
            self.abuse_report += ["User Response: " + message.content + "\n"]
            self.stage = 6
            return self.block_action(message)
            # return ["Thank you for providing more information. Would you like to block the user whose content you reported? \n Please enter 1 for Yes, or 2 for No"]

            # return ["Thank you for providing more information. Please enter `confirm` to submit the report, or `cancel` to cancel the report."]
        if (self.stage == 7):
            if (message.content == "confirm"):
                self.stage = 0
                self.state = State.REPORT_COMPLETE
                return ["Report sent!"]
            elif (message.content == self.CANCEL_KEYWORD):
                self.stage = 0
                self.state = State.REPORT_CANCELLED
                return ["Report cancelled."]
            else: 
                return ["Invalid input. Please enter `confirm` to submit the report, or `cancel` to cancel the report."]
        #     if (self.report_type == "Violence"):
        #         self.state = State.REPORT_COMPLETE
        #         self.stage = 3
        #         return ["Thank you for reporting this content. Our moderation team will review and decide on an appropriate course of action, which could involve notifying local authorities."]
        #     if (self.report_type == "Harassment" and message.content == "3"):
        #         self.stage = 4
        #         self.abuse_report += ['Response: ' + message.content + ': ' + types[message.content] + "\n"]
        #         return self.age_verification_action(message)
        #     if (self.report_type == "Sensitive or Offensive Content" and message.content == "3"):
        #         self.stage = 5
        #         self.abuse_report += [message.content + ': ' + types[message.content] + "\n"]
        #         return self.CSAM_action(message)
        #     if (["1", "2", "3", "4", "5", "6"].__contains__(message.content)):
        #         self.abuse_report += ["Reponse: " + message.content + ': ' + replies[message.content] + "\n"]
        #         self.stage = 6
        #         return self.block_action(message)
        #     else:
        #         return ["Invalid input. Please try again."]
            
        # if (self.stage == 3):
        #     self.abuse_report += ["User Response: " + message.content + "\n"]
        #     if (message.content == "confirm"):
        #         self.stage = 0
        #         self.state = State.REPORT_COMPLETE
        #         return ["Report sent!"]
        #     else:
        #         self.stage = 0
        #         self.state = State.REPORT_CANCELLED
        #         return ["Report cancelled."]
        if (self.stage == 4):
            self.abuse_report += ["User Response: " + message.content + "\n"]
            return self.age_verification_action(message)      
        if (self.stage == 5):
            self.abuse_report += ["User Response: " + message.content + "\n"]
            return self.CSAM_action(message)
        if (self.stage == 6):
            # self.abuse_report += ["User Response: " + message.content + "\n"]
            return self.block_action(message)
            
    def age_verification_action(self, message):
        if (self.age_stage == 0):
            self.abuse_report += ["Are you over 18?\n1. Yes\n2. No \n"]
            self.age_stage = 1
            return ["Are you over 18?\n1. Yes\n2. No"]
        if (self.age_stage == 1):
            # self.abuse_report += ["User Response: " + message.content + "\n"]
            if (message.content == "2"):
                self.age_stage = 2
                self.abuse_report += ["1. The user is trying to get close to me, asking me personal information, or showing signs of “grooming,” asking me for sexual material.\n2. Does not apply"]

                return ["1. The user is trying to get close to me, asking me personal information, or showing signs of “grooming,” asking me for sexual material.\n2. Does not apply"]
            elif (message.content == "1"):
                self.age_stage = 0
                self.stage = 6
                return self.block_action(message)
            else:
                return ["Invalid input. Please try again."]
        if (self.age_stage == 2):
            #TODO fix this
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
            # self.abuse_report += ["What type of material?\n1. Images or Videos\n2. External Links\n3. Other\n"]
            self.CSAM_stage = 1
            return ["What type of material?\n1. Images or Videos\n2. External Links\n3. Other"]
        if (self.CSAM_stage == 1):
            # self.abuse_report += ["User Response: " + message.content + "\n"]
            if ["1", "2", "3",].__contains__(message.content):
                self.abuse_report += ["User Response: " + message.content + ' ' + Report.TYPE_OF_CSAM_MATERIAL[message.content]+ "\n"]
            if (message.content == "1" or message.content == '2'):
                self.CSAM_stage = 0
                self.stage = 6
                return self.block_action(message)
            # elif (message.content == "2"):
            #     self.CSAM_stage = 0
            #     self.stage = 6
            #     return self.block_action(message)
            elif (message.content == "3"):
                self.CSAM_stage = 2
                return ["Please provide a description of the material."]
            else:
                return ["Invalid input. Please try again."]
        if (self.CSAM_stage == 2):
            self.abuse_report += ["Description: " + message.content + "\n"]
            print(message.content)
            self.CSAM_stage = 0
            self.stage = 6
            return self.block_action(message)
        else:
            return ["Invalid input. Please try again."]

    def block_action(self, message):
        if (self.block_stage == 0):
            # self.abuse_report += ["Would you like to block the user?\n1. Yes\n2. No\n"]
            self.block_stage = 1
            return ["Would you like to block the user?\n1. Yes\n2. No"]
        if (self.block_stage == 1):
            reply = "Thank you for reporting this content. Our moderation team will review and decide on an appropriate course of action, which could include post/content removal, a warning, account removal, or even notifying local authorities if necessary.\n\n"
            if (message.content == "1"):
                #TODO: Store info from message 
                print("todo: store info from message")
                self.abuse_report += ["Decision on Blocking User: " + "Block user" + "\n"]

                self.block_stage = 0
                self.stage = 0
                self.state = State.REPORT_COMPLETE
                return [reply]
            if (message.content == "2"):
                self.abuse_report += ["Decision on Blocking User: " + "Do not block user" + "\n"]
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
            self.state = State.REPORT_CANCELLED
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
    
    def return_abuse_report(self):
        return self.abuse_report

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
    def report_cancelled(self):
        return self.state == State.REPORT_CANCELLED
    
class ModReport:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.solicitation_flag = False
        self.stage = 0
        self.original_message = None

    async def handle_mod_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''
        if self.stage == -1:
            self.state = State.REPORT_COMPLETE
            return ["Your report has been completed."]
        if self.stage == 0 and not message.author.bot: 
            self.original_message = message
            reply = "Is this content CSAM? Please reply 'yes' or 'no'."
            self.stage = 2
            return [reply]
        if self.stage == 2:
            if message.content == "yes" or message.content == "Yes":
                reply = "Please indicate which type of CSAM material this content is.\n"
                reply += "1: Child grooming \n"
                reply += "2: Offering to share CSAM content\n"
                reply += "3: CSAM solicitiation\n"
                reply += "4: Offering to sell CSAM\n"
                reply += "5: Other"
                self.stage = 3
                return [reply]
            elif message.content == "no" or message.content == "No":
                self.stage = State.REPORT_COMPLETE
                return ["Thank you for your help - please use the DM reporting flow.\nYour report has been completed."]
            return ["Please reply yes or no."]
        if self.stage == 3:
            legal_messages = [i+1 for i in range(5)]
            if int(message.content) not in legal_messages:
                self.stage = 2
                return ["Please select an option above."]
            if int(message.content) <= 1:
                self.stage = 4
                return ["Is this content targeted toward a person age 18 or older? Please reply yes or no."]
            elif int(message.content) < 5:
                self.solicitation_flag = True
                self.stage = 4
                reply = "Does it match levels 2 or above of the COPINE scale?\n"
                reply += "1: Yes\n"
                reply += "2: No\n"
                reply += "3: No, but the content is in an inappropriate context.\n"
                return [reply]
            return ["Please reach out directly to our higher level review team."]
        if self.stage == 4:
            print(self.solicitation_flag)
            print(message.content)
            if self.solicitation_flag is False:
                if message.content == "yes" or message.content == "Yes":
                    self.stage = -1
                    self.state = State.REPORT_COMPLETE
                    return ["This material does not appear to be CSAM. No action has been taken at this time. Please reach out to our Trust and Safety team if you have further concerns."]
                elif message.content == "no" or message.content == "No":
                    self.stage = -1
                    self.state = State.REPORT_COMPLETE
                    reply = "Thank you for your report. We take these matters very seriously.\n"
                    reply += "We have reported this content to the National Center for Missing & Exploited Children\n"
                    reply += "and banned this user. The content has been removed."
                    if (self.original_message is not None):
                        await self.original_message.delete()
                    return [reply]
            else:
                if int(message.content) == 3:
                    self.stage = -1
                    self.state = State.REPORT_COMPLETE
                    return ["We have flagged this content and have sent it to our dedicated higher-level review team. Thank you for your report."]
                elif int(message.content) == 1:
                    self.stage = -1
                    self.state = State.REPORT_COMPLETE
                    reply = "Thank you for your report. We take these matters very seriously.\n"
                    reply += "We have reported this content to the National Center for Missing & Exploited Children\n"
                    reply += "and banned this user. The content has been removed."
                    if (self.original_message is not None):
                        await self.original_message.delete()
                        await self.original_message.author.send(f"We have deleted your message: \n >{self.original_message.content}\nin {self.original_message.guild} for violating our policies on CSAM. You have been kicked from the server.")
                    return [reply]
                else:
                    self.stage = -1
                    self.state = State.REPORT_COMPLETE
                    return ["This material does not appear to be CSAM. No action has been taken at this time. Please reach out to our Trust and Safety team if you have further concerns."]
                    # Not implementing bans since we are in 152 server. - sammym
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
      

