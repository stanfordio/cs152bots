from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    LEVEL1 = auto()
    LEVEL2 = auto()
    REPORT_SUBMITTED = auto()
    BLOCKING = auto()
    REPORT_COMPLETE = auto()
    CHECK_DANGER = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    OFFENSIVE_CONTENT = ""
    AUTHOR = ""
    REASON = ""
    SUB_CAT = ""
    OTHER_INFO = ""

    def __init__(self, client, add_to_queue_callback):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.add_to_queue = add_to_queue_callback
    
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
            self.OFFENSIVE_CONTENT = message.content
            self.AUTHOR = message.author.name
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Is this the message you would like to report? \nSay 'yes' to confirm and 'no' to report a different message."]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content.lower() == 'no':
                self.state =  State.AWAITING_MESSAGE
                return ["Please copy paste the link to the message you want to report.\nYou can obtain this link by right-clicking the message and clicking `Copy Message Link`."]
            elif message.content.lower() == 'yes':
                self.state = State.LEVEL1
                reply = "Please select the most appropriate reason for reporting this message and reply with the associated number.\n"
                reply += "1: Explicit Content\n"
                reply += "2: Harassment\n"
                reply += "3: Spam\n"
                reply += "4: Potential Danger"
                return [reply]
            else:
                return ["Sorry I didn't understand that. \nSay 'yes' to confirm you want to report:", \
                         "```" + self.OFFENSIVE_CONTENT + "```" +  "and 'no' to report a different message."]
        
        if self.state == State.LEVEL1:
            # this is where the user has chosen the reason for reporting and will be prompted for more specific info
            if message.content == "1":
                # explicit content flow...main direction for us (CSAM)
                self.REASON = "Explicit Content"
                self.state = State.LEVEL2
                reply = "Please select the form of explicit content that best characterizes this content and reply with the associated number.\n"
                reply += "1: Child Sexual Abuse Material\n"
                reply += "2: Violent Acts\n"
                reply += "3: Substance Abuse\n"
                reply += "4: Nudity or Sexual Activity\n"
                reply += "5: Other\n"
                reply += "To choose a different reason for reporting, please say 'back'"
                return [reply]
            
            elif message.content == "2":
                # Harassment...follow the flow down here
                self.REASON = "Harassment"
                self.state = State.LEVEL2
                reply = "Please select the form of harassment that best characterizes this content and reply with the associated number.\n"
                reply += "1: Bullying\n"
                reply += "2: Sextortion\n"
                reply += "3: Grooming\n"
                reply += "4: Sexual Harassment\n"
                reply += "5: Hate Speech\n"
                reply += "6: Other\n"
                reply += "To choose a different reason for reporting, please say 'back'"
                return [reply]
            
            elif message.content == "3":
                # spam
                self.REASON = "Spam"
                self.state = State.LEVEL2
                reply = "Please select the form of spam that best characterizes this content and reply with the associated number.\n"
                reply += "1: Impersonation\n"
                reply += "2: Solicitation\n"
                reply += "3: Phishing\n"
                reply += "4: Sale of Illegal or Regulated Goods\n"
                reply += "5: Other\n"
                reply += "To choose a different reason for reporting, please say 'back'"
                return [reply]
            
            elif message.content == "4":
                # potential danger
                self.REASON = "Potential Danger"
                self.state = State.LEVEL2
                reply = "Please select the form of potential danger that best characterizes this content and reply with the associated number.\n"
                reply += "1: Self Harm\n"
                reply += "2: Terrorism\n"
                reply += "3: Threat to Public Safety\n"
                reply += "4: Dangerous Organizations\n"
                reply += "5: Other\n"
                reply += "To choose a different reason for reporting, please say 'back'"
                return [reply]
            
            else:
                # didn't understand
                return ["Sorry I didn't understand that. Please answer with a digit 1-4."]
        
        if self.state == State.LEVEL2:
            # at this point, message.content is the type of specific content violation
            # this is where the user has chosen their more specific reporting reason and will either submit or add more info
            if message.content == 'back':
                self.state = State.LEVEL1
                reply = "Please select the most appropriate reason for reporting this message and reply with the associated number.\n"
                reply += "1: Explicit Content\n"
                reply += "2: Harassment\n"
                reply += "3: Spam\n"
                reply += "4: Potential Danger"
                return [reply]
            
            # when the reason for reporting was explicit content
            # if self.REASON == "Explicit Content":

            #     # ensure the user's reply is one of the options
            #     if message.content not in ["1", "2", "3", "4", "5"]:
            #         # if it's not one of the options then tell them to try again basically
            #         return ["Sorry I didn't understand that. Please answer with a digit 1-5."]
            #     my_dict = {"1" : "Child Sexual Abuse Material", "2" : "Violent Acts", "3" : "Substance Abuse", "4" : "Nudity or Sexual Material", "5" : "Other"}
            #     self.SUB_CAT = my_dict[message.content]
            if self.REASON == "Explicit Content":
                # Ensure user's reply is valid
                if message.content not in ["1", "2", "3", "4", "5"]:
                    return ["Sorry I didn't understand that. Please answer with a digit 1-5."]
                my_dict = {
                    "1": "Child Sexual Abuse Material",
                    "2": "Violent Acts",
                    "3": "Substance Abuse",
                    "4": "Nudity or Sexual Activity",
                    "5": "Other"
                }
                self.SUB_CAT = my_dict[message.content]
                self.state = State.CHECK_DANGER  # Move to check danger state
                return ["Does this report involve imminent danger? Please reply 'yes' or 'no'."]
            
            
            # when the reason was spam or harassment
            elif self.REASON == "Harassment" or self.REASON == "Spam":

                # when the reason was harassment specifically
                if self.REASON == "Harassment":
                    # ensure the user's reply is one of the options
                    if message.content not  in ["1", "2", "3", "4", "5", "6"]:
                        return ["Sorry I didn't understand that. Please answer with a digit 1-6."]
                    my_dict = {"1" : "Bullying", "2" : "Sextortion", "3" : "Grooming", "4" : "Sexual Harassment", "5" : "Hate Speech", "6": "Other"}
                    self.SUB_CAT = my_dict[message.content]
                
                # the reason was spam
                else:
                    # ensure the user's reply is one of the options
                    if message.content not  in ["1", "2", "3", "4", "5"]:
                        return ["Sorry I didn't understand that. Please answer with a digit 1-5."]
                    my_dict = {"1" : "Impersonation", "2" : "Solicitation", "3" : "Phishing", "4" : "Sale of Illegal or Regulated Goods", "5" : "Other"}
                    self.SUB_CAT = my_dict[message.content]
            
            # reason must be potential danger
            else:
                # ensure the user's reply is one of the options
                if message.content not  in ["1", "2", "3", "4", "5"]:
                    return ["Sorry I didn't understand that. Please answer with a digit 1-5."]
                my_dict = {"1" : "Self Harm", "2" : "Terrorism", "3" : "Threat to Public Safety", "4" : "Dangerous Organizations", "5" : "Other"}
                self.SUB_CAT = my_dict[message.content]
            
            self.state = State.REPORT_SUBMITTED
            return ["Please add any further information, context, or thoughts to be shared with our content moderation team or say ‘no’ to submit."]
        if self.state == State.CHECK_DANGER:
            if message.content.lower() == 'yes':
                self.IMMINENT_DANGER = True
                self.SUB_CAT += " Danger"  # Optionally append " Danger" to SUB_CAT
            elif message.content.lower() == 'no':
                self.IMMINENT_DANGER = False
            else:
                return ["Sorry, I didn't understand that. Does this report involve imminent danger? Please reply 'yes' or 'no'."]
            self.state = State.REPORT_SUBMITTED
            return ["Please add any further information, context, or thoughts to be shared with our content moderation team or say ‘no’ to submit."]
        
    
        if self.state == State.REPORT_SUBMITTED:
            self.add_to_queue(self)  # Add the report to the appropriate queue
            self.OTHER_INFO = message.content
            reply = "Would you like to block ```{}```Say 'yes' to block and 'no' not to block.".format(self.AUTHOR)
            self.state = State.BLOCKING
            return [reply]
        
        if self.state == State.BLOCKING:
            reply = ""
            if message.content.lower() == "yes":
                # BLOCK USER HERE
                reply = "User:" + "```" + self.AUTHOR + "```" + "Has been blocked.\n\n"
            reply += "Thank you for reporting. Your report has been submitted\n"
            reply += "Our content moderation team will promptly review this report and determine the most appropriate course of action, including notifying appropriate law enforcement agencies, post removal, or account removal."
            self.state = State.REPORT_COMPLETE
            return [reply]

            

    def report_complete(self):
        ''' Debugging stuff below:
        OFFENSIVE_CONTENT = ""
        AUTHOR = ""
        REASON = ""
        SUB_CAT = ""
        OTHER_INFO = ""
        to_print = "Author: {}\n".format(self.AUTHOR)
        to_print += "Message: {}\n".format(self.OFFENSIVE_CONTENT)
        to_print += "Reason Level 1: {}\n".format(self.REASON)
        to_print += "Reason Level 2: {}\n".format(self.SUB_CAT)
        to_print += "Additional Info: {}".format(self.OTHER_INFO)
        print(to_print)
        '''
        return self.state == State.REPORT_COMPLETE
    


    

