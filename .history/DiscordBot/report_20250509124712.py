from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()

    AWAITING_REASON = auto()
    AWAITING_DISINFORMATION_TYPE = auto()
    AWAITING_POLITICAL_DISINFORMATION_TYPE =auto()
    AWAITING_HEALTHL_DISINFORMATION_TYPE =auto()
    AWAITING_FILTER_ACTION = auto()
    AWAITING_HARMFUL_CONTENT_STATUS = auto()

    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

        self.message_guild_id = None
        self.reported_author = None
        self.reported_content = None
        self.report_type = None
        self.disinfo_type = None
        self.disinfo_subtype = None
        self.filter = False
        self.harmful = None
    
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
        else:
            if message.content == self.START_KEYWORD:
                reply = "You currently have an active report open, the status is " + self.state.name + ". "
                reply += "Please continue this report or say `cancel` to cancel.\n"
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

            self.state = State.AWAITING_REASON

            # add guild ID so we know where to send the moderation todo
            self.message_guild_id = message.guild.id

            self.reported_author = message.author.name
            self.reported_content = message.content

            reply = "I found this message:```" + message.author.name + ": " + message.content + "```\n"
            reply += "Please select the reason for reporting this message by typing the corresponding number:\n"
            reply += "1. Disinformation\n"
            reply += "2. Other\n"
            return [reply]
        
        if self.state == State.AWAITING_REASON:
            # Process user's report reason 

            if message.content == "1":
                # Handling disinformation
                self.report_type = "Disinformation"
                self.state = State.AWAITING_DISINFORMATION_TYPE

                reply = "You have selected " + self.report_type + ".\n"
                reply += "Please select the type of disinformation by typing the corresponding number:\n"
                reply += "1. Political Disinformation\n"
                reply += "2. Health Disinformation\n"
                reply += "3. Other Disinformation\n"
                return [reply]
            
            elif message.content == "2" :
                # Handling Other Abuse types
                self.report_type = "Other"
                # self.disinfo_type = "[out of scope of project]"
                # self.disinfo_subtype = "[out of scope of project]"
                self.state = State.REPORT_COMPLETE
                # return [
                #         "Thank you for reporting " + self.report_type + " content.",
                #         "Our content moderation team will review the message and take action which may result in content or account removal."
                #         ]
                reply = "Thank you for reporting " + self.report_type + " content.\n"
                reply += "Our content moderation team will review the message and take action which may result in content or account removal.\n"
                return [reply]
            
            # elif message.content == "3" :
            #     # Handling Harassment
            #     self.report_type = "Harassment"
            #     self.disinfo_type = "[out of scope of project]"
            #     self.disinfo_subtype = "[out of scope of project]"
            #     self.state = State.REPORT_COMPLETE
            #     return [
            #             "Thank you for reporting " + self.report_type + " content.",
            #             "Our content moderation team will review the message and take action which may result in content or account removal."
            #             ]
            

            # elif message.content == "4" :
            #     # Handling Spam
            #     self.report_type = "Spam"
            #     self.disinfo_type = "[out of scope of project]"
            #     self.disinfo_subtype = "[out of scope of project]"
            #     self.state = State.REPORT_COMPLETE
            #     return [
            #             "Thank you for reporting " + self.report_type + " content", 
            #             "Our content moderation team will review the message and take action which may result in content or account removal."
            #             ]
                        
            else:
                # Handling wrong report reason
                reply = "Kindly enter a valid report reason by selecting the correponding number:\n"
                reply += "1. Disinformation\n"
                reply += "2. Other\n"
                reply += "Please try again or say `cancel` to cancel.\n"
                return [reply]

        if self.state == State.AWAITING_DISINFORMATION_TYPE :
            # Process Disinformation options

            if message.content == "1":
                # Handle political disinformation
                self.state = State.AWAITING_POLITICAL_DISINFORMATION_TYPE
                self.disinfo_type = "Political Disinformation"
                reply = "You have selected " + self.disinfo_type + ".\n"
                reply += "Please select the type of political Disinformation by typing the corresponding number:\n"
                reply += "1. Election/Campaign Misinformation\n"
                reply += "2. Government/Civic Services\n"
                reply += "3. Manipulated Photos/Video\n"
                reply += "4. Other\n"
                return [reply]
            
            elif message.content == "2" :
                # Handle Health Disinformation
                self.state = State.AWAITING_HEALTHL_DISINFORMATION_TYPE
                self.disinfo_type = "Health Disinformation"
                reply = "You have selected " + self.disinfo_type + ".\n"
                reply += "Please select the type of health disinformation by typing the corresponding number:\n"
                reply += "1. Vaccines\n"
                reply += "2. Cures and Treatments\n"
                reply += "3. Mental Health\n"
                reply += "4. Other\n"
                return [reply]


            elif message.content == "3" :
                # Handle other Disinformation
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                self.disinfo_type = "Other Disinformation"
                self.disinfo_subtype = "[out of scope of project]"
                reply = "You have selected " + self.disinfo_type + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]
            
            else :
                # Handling wrong disinformation type
                reply = "Kindly enter a valid disinformation type by selecting the correponding number:\n"
                reply += "1. Political Disinformation\n"
                reply += "2. Health Disinformation\n"
                reply += "3. Other Disinformation\n"
                reply += "Please try again or say `cancel` to cancel.\n"
                return [reply]

        if self.state == State.AWAITING_POLITICAL_DISINFORMATION_TYPE :
            # Process political disinformation options

            if message.content == "1":
                # Handling Election/Campaign Misinformation
                self.disinfo_subtype = "Election/Campaign Misinformation"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]
            
            elif message.content == "2":
                 # Handling Government/Civic Services
                self.disinfo_subtype = "Government/Civic Services"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]

            elif message.content == "3":
                 # Handling Manipulated Photos/Video
                self.disinfo_subtype = "Manipulated Photos/Video"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]
            
            elif message.content == "4":
                 # Handling Other
                self.disinfo_subtype = "Other"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]

            else :
                # Handling wrong political disinformation type
                reply = "Please select the type of political Disinformation by typing the corresponding number:\n"
                reply += "1. Election/Campaign Misinformation\n"
                reply += "2. Government/Civic Services\n"
                reply += "3. Manipulated Photos/Video\n"
                reply += "4. Other\n"
                reply += "Please try again or say `cancel` to cancel."
                return [reply]
        
        if self.state == State.AWAITING_HEALTHL_DISINFORMATION_TYPE:
            # Process health disinformation options

            if message.content == "1":
                # Handling Vaccines
                self.disinfo_subtype = "Vaccines"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]
            
            elif message.content == "2":
                 # Handling Cures and Treatments
                self.disinfo_subtype = "Cures and Treatments"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]

            elif message.content == "3":
                 # Handling Mental Health
                self.disinfo_subtype = "Mental Health"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]
            
            elif message.content == "4":
                 # Handling Other
                self.disinfo_subtype = "Other"
                self.state = State.AWAITING_HARMFUL_CONTENT_STATUS
                reply = "You have selected " + self.disinfo_subtype + ".\n"
                reply += "Could this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                return [reply]
            
            else :
                # Handling wrong health disinformation type
                reply = "Please select the type of health Disinformation by typing the corresponding number:\n"
                reply += "1. Vaccines\n"
                reply += "2. Cures and Treatments\n"
                reply += "3. Mental Health\n"
                reply += "4. Other\n"
                reply += "Please try again or say `cancel` to cancel."
                return [reply]

        if self.state == State.AWAITING_HARMFUL_CONTENT_STATUS:
            # Handle decision making on whether content is harmful

            if message.content == "1" :
                # No harmful content 
                self.state = State.AWAITING_FILTER_ACTION
                reply = "Please indicate if you would like to block content from this account on your feed. Select the correponding number:\n"
                reply += "1. No \n"
                reply += "2. Yes \n"
                return [reply]
            
            elif message.content in ["2", "3", "4"] :
                # Harmful content
                harm_dict = {
                    "2": "physical",
                    "3": "mental",
                    "4": "financial"
                }
                self.harmful = harm_dict[message.content]
                self.state = State.AWAITING_FILTER_ACTION
                reply = "Thank you. Our team has been notified.\n"
                reply += "Please indicate if you would like to block content from this account on your feed. Select the correponding number:\n"
                reply += "1. No \n"
                reply += "2. Yes \n"
                return [reply]

            else:
                # Handle wrong response to harmful prompt 
                reply = "Kindly indicate if this content likely cause imminent harm to people or public safety? Select the correponding number:\n"
                reply += "1. No.\n"
                reply += "2. Yes, physical harm.\n"  
                reply += "3. Yes, mental harm.\n"  
                reply += "4. Yes, financial or property harm.\n"  
                reply += "Please try again or say `cancel` to cancel."
                return [reply]


        if self.state == State.AWAITING_FILTER_ACTION:
            # Handling responses to filter account content

            if message.content == "1":
                # Handle no content filtering action
                self.state = State.REPORT_COMPLETE
                reply = "Thank you for reporting " + self.report_type + " content.\n"
                reply += "Our content moderation team will review the message and take action which may result in content or account removal.\n"
                return [reply]
            
            elif message.content == "2":
                # Handle content filtering action
                self.filter = True
                self.state = State.REPORT_COMPLETE
                reply = "Thank you for reporting " + self.report_type + " content.\n"
                reply += "Our content moderation team will review the message and take action which may result in content or account removal.\n"
                return [reply]

            else:
                # wrong option for account filtering prompt 
                reply = "Would you like to filter content from this account on your feed? Select the correponding number:\n"
                reply += "1. Yes\n"
                reply += "2. No\n"       
                reply += "Please try again or say `cancel` to cancel."
                return [reply]

#         if self.state == State.BLOCK_STEP:
#             # if user wants to block then block
#             user_wants_to_block = True
#             return [user_wants_to_block]
            
        return {}
    
    #getters for state
    def get_message_guild_id(self):
        return self.message_guild_id
    def get_reported_author(self):
        return self.reported_author
    def get_reported_content(self):
        return self.reported_content
    def get_report_type(self):
        return self.report_type
    def get_disinfo_type(self):
        return self.disinfo_type
    def get_disinfo_subtype(self):
        return self.disinfo_subtype
    def get_harmful(self):
        return self.harmful
    def get_filter(self):
        return self.filter
    
    def is_report_start(self):
        return self.state == State.REPORT_START
    def is_awaiting_message(self):
        return self.state == State.AWAITING_MESSAGE
    def is_awaiting_reason(self):
        return self.state == State.AWAITING_REASON
    def is_awaiting_disinformation_type(self):
        return self.state == State.AWAITING_DISINFORMATION_TYPE
    def is_awaiting_political_disinformation_type(self):
        return self.state == State.AWAITING_POLITICAL_DISINFORMATION_TYPE
    def is_awaiting_healthl_disinformation_type(self):
        return self.state == State.AWAITING_HEALTHL_DISINFORMATION_TYPE
    def is_awaiting_harmful_content_status(self):
        return self.state == State.AWAITING_HARMFUL_CONTENT_STATUS
    def is_awaiting_filter_action(self):
        return self.state == State.AWAITING_FILTER_ACTION
    # def block_step(self):
    #     return self.state == State.BLOCK_STEP
    def is_report_complete(self):
        return self.state == State.REPORT_COMPLETE    

