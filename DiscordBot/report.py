from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()

#     CATEGORY_IDENTIFIED = auto() #disinformation, nudity, etc
#     TYPE_IDENTIFIED = auto() #political disinfo, health disinfo
#     SUBTYPE_IDENTIFIED = auto() #vaccines, cures and treatments
#     HARM_IDENTIFIED = auto()
#     BLOCK_STEP = auto()

    REPORT_COMPLETE = auto()
    AWAITING_REASON = auto()
    AWAITING_DISINFORMATION_TYPE = auto()
    AWAITING_POLITICAL_DISINFORMATION_TYPE =auto()
    AWAITING_FILTER_ACTION = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_type = None
        self.disinfo_type = None
        self.political_disinfo_type = None
        self.filter = False
    
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
#             return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
#                     "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
              return ["I found this message:```" + message.author.name + ": " + message.content + "```\n",
                    message.author.name,
                    message.content]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            # Ask the user to select a reason for reporting the message
            self.state = State.AWAITING_REASON
            return [
            "Please select the reason for reporting this message by typing the corresponding number:",
            "1. Disinformation",
            "2. Hate Speech",
            "3. Harassment",
            "4. Spam"
            ]
        
        if self.state == State.AWAITING_REASON:
            # Process user's report reason 

            if message.content == "1":
                # Handling disinformation
                self.report_type = "Disinformation"
                self.state = State.AWAITING_DISINFORMATION_TYPE
                return[
                    "Please select the type of disinformation by typing the corresponding number:",
                    "1. Political Disinformation",
                    "2. Health Disinformation",
                    "3. Other Disinformation"
                ]
            
            elif message.content == "2" :
                # Handling hate speech
                self.report_type = "Hate Speech"
                self.state = State.REPORT_COMPLETE
                return [" Thank you for reporting" + self.report_type + " content. Our content moderation team will review the message and take action which may result in content or account removal."]
            
            elif message.content == "3" :
                # Handling Harassment
                self.report_type = "Harassment"
                self.state = State.REPORT_COMPLETE
                return [" Thank you for reporting" + self.report_type + " content. Our content moderation team will review the message and take action which may result in content or account removal."]
            

            elif message.content == "4" :
                # Handling Spam
                self.report_type = "Spam"
                self.state = State.REPORT_COMPLETE
                return [" Thank you for reporting" + self.report_type + " content. Our content moderation team will review the message and take action which may result in content or account removal."]
                        
            else:
                # Handling wrong report reason
                return [ "Kindly enter a valid report reason by selecting the correponding number:",
                            "1. Disinformation",
                            "2. Hate Speech",
                            "3. Harassment",
                            "4. Spam",
                            "Please try again or say `cancel` to cancel."
                        ]

        if self.state == State.AWAITING_DISINFORMATION_TYPE :
            # Process Disinformation options

            if message.content == "1":
                # Handle political disinformation
                self.state = State.AWAITING_POLITICAL_DISINFORMATION_TYPE
                self.disinfo_type = "Political Disinformation"
                return [ "Please select the type of political Disinformation by typing the corresponding number:",
                            "1. Conspiracy Theory",
                            "2. Distorted Information",
                            "3. False Claim",
                            "4. Election/Campaign Misinformation"
                ]
            
            elif message.content == "2" :
                # Handle Health Disinformation
                self.state = State.AWAITING_FILTER_ACTION
                self.disinfo_type = "Health Disinformation"
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No"
                ]


            elif message.content == "3" :
                # Handle other Disinformation
                self.state = State.AWAITING_FILTER_ACTION
                self.disinfo_type = "Other Disinformation"
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No"
                ]
            
            else :
                # Handling wrong disinformation type
                return [ "Kindly enter a valid disinformation type by selecting the correponding number:",
                            "1. Political Disinformation",
                            "2. Health Disinformation",
                            "3. Other Disinformation",
                            "Please try again or say `cancel` to cancel."
                        ]

        if self.state == State.AWAITING_POLITICAL_DISINFORMATION_TYPE :
            # Process political disinformation options

            if message.content == "1":
                # Handling Conspiracy Theory
                self.political_disinfo_type = "Conspiracy Theory"
                self.state = State.AWAITING_FILTER_ACTION
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No"
                ]
            
            elif message.content == "2":
                 # Handling Distorted Information
                self.political_disinfo_type = "Distorted Information"
                self.state = State.AWAITING_FILTER_ACTION
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No"
                ]

            elif message.content == "3":
                 # Handling False Claim
                self.political_disinfo_type = "False Claim"
                self.state = State.AWAITING_FILTER_ACTION
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No"
                ]
            
            elif message.content == "4":
                 # Handling Election/Campaign Misinformation
                self.political_disinfo_type = "Election/Campaign Misinformation"
                self.state = State.AWAITING_FILTER_ACTION
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No"
                ]

            
            else :
                # Handling 
                return [ "Please select the type of political Disinformation by typing the corresponding number:",
                            "1. Conspiracy Theory",
                            "2. Distorted Information",
                            "3. False Claim",
                            "4. Election/Campaign Misinformation",
                            "Please try again or say `cancel` to cancel."
                        ]
            
        if self.state == State.AWAITING_FILTER_ACTION:
            # Handling responses to filter account content

            if message.content == "1":
                # Handle content filtering
                self.filter = True
                self.state = State.REPORT_COMPLETE
                return [    "This account’s posts have been restricted from appearing on your feed.",
                            " Thank you for reporting" + self.report_type + " content. Our content moderation team will review the message and take action which may result in content or account removal."
                        ]
            
            elif message.content == "2":
                # Handle no content filtering action
                self.state = State.REPORT_COMPLETE
                return [    "This account’s posts have been restricted from appearing on your feed.",
                            " Thank you for reporting" + self.report_type + " content. Our content moderation team will review the message and take action which may result in content or account removal."
                        ]

            else :
                # wrong option for account filtering prompt 
                return [ "Would you like to filter content from this account on your feed? Select the correponding number:",
                            "1. Yes",
                            "2. No",
                            "Please try again or say `cancel` to cancel."
                ]
            
            
        return []

#         if self.state == State.BLOCK_STEP:
#             # if user wants to block then block
#             user_wants_to_block = True
#             return [user_wants_to_block]

        return []
    
    
    def report_start(self):
        return self.state == State.REPORT_START
    def awaiting_message(self):
        return self.state == State.AWAITING_MESSAGE
    def message_identified(self):           
        return self.state == State.MESSAGE_IDENTIFIED
    def category_identified(self):
        return self.state == State.CATEGORY_IDENTIFIED
    def type_identified(self):
        return self.state == State.TYPE_IDENTIFIED
    def subtype_identified(self):
        return self.state == State.SUBTYPE_IDENTIFIED
    def harm_identified(self):
        return self.state == State.HARM_IDENTIFIED
    def block_step(self):
        return self.state == State.BLOCK_STEP
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    

# when self.state == report.coplte what should we do ?
    

