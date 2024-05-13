from constants import UserResponse, USER_REPORT_KEY, SpecificIssue
from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    AWAITING_ISSUE_CATEGORY = auto()
    AWAITING_SPECIFIC_ISSUE = auto()
    AWAITING_MORE_INFORMATION = auto()  # TODO: implement this. should be used for 5. Other
    AWAITING_SOURCE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.user_responses = {}
    
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
            reply =  "Thank you for starting the reporting process. Help us understand the problem. What is wrong with this ad?\n"
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.user_responses["reporter"] = message.author.name
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

            self.state = State.MESSAGE_IDENTIFIED

            self.message = message
            reply = "Is this the message you wanted to report? (y/n) \n \n"
            reply += f'{message.author.name}: "{message.content}"'

            return [reply]

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content == 'y':
                return self.request_issue_category()
            elif message.content == 'n':
                self.state = State.AWAITING_MESSAGE
                return ["Please enter the correct link for the message you'd like to report."]
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"]

        elif self.state == State.AWAITING_ISSUE_CATEGORY:
            return self.request_specific_issue(message)

        elif self.state == State.AWAITING_SPECIFIC_ISSUE:
            return self.request_source(message)

        elif self.state == State.AWAITING_SOURCE:
            self.state = State.REPORT_COMPLETE
            return self.finish_report(message)

        return []
        
    def request_issue_category(self):
        reply =  "Please select the category that best describes your report:\n"
        reply += "1. Misleading or false information\n"
        reply += "2. Inappropriate Adult Content\n"
        reply += "3. Illegal products and services\n"
        reply += "4. Offensive content\n"
        reply += "5. Other\n"
        self.state = State.AWAITING_ISSUE_CATEGORY
        return [reply]

    def request_specific_issue(self, message):
        if int(message.content) in [1, 2, 3, 4, 5]:
            report_category = int(message.content)
            report_category_name = USER_REPORT_KEY[report_category]["name"]
            self.user_responses[UserResponse.ABUSE_TYPE] = report_category
            self.state = State.AWAITING_SPECIFIC_ISSUE
            
            reply = f"Thank you. The message has been flagged as {report_category}. {report_category_name}. \n"
            reply += f"Please select the type of {report_category_name.lower()}: \n"
            
            for i in range(1, len(USER_REPORT_KEY[report_category].keys())):
                description = USER_REPORT_KEY[report_category][i]
                if i == len(USER_REPORT_KEY[report_category].keys()) - 1:
                    reply += f"{i}. {description}"
                else:
                    reply += f"{i}. {description}\n"

            return [reply]
        else:
            return ["Invalid response, please type the number corresponding with the issue category."]

    def request_source(self, message):
        # TODO: make sure the number is correct based on the previous category 
        # Only called if it is a report of political disinformation
        if int(message.content) in [SpecificIssue.POLITICAL] and self.user_responses[UserResponse.ABUSE_TYPE] in [SpecificIssue.DISINFORMATION]:
            self.user_responses[UserResponse.SPEC_ISSUE] = int(message.content)
            self.state = State.AWAITING_SOURCE

            return ["Please explain the issue with the ad, or provide any sources you might have that could help disprove. Type 'none' if you don't have any."]
        elif self.user_responses[UserResponse.ABUSE_TYPE] in [SpecificIssue.OTHER]:
            self.user_responses[UserResponse.SPEC_ISSUE] = int(message.content)
            self.state = State.AWAITING_SOURCE
            category = USER_REPORT_KEY[self.user_responses[UserResponse.ABUSE_TYPE]][int(message.content)].lower()

            return [f"Please specify what you are reporting with respect to {category}."]
        elif int(message.content) in [1, 2, 3, 4]:
            self.user_responses[UserResponse.SPEC_ISSUE] = int(message.content)
            self.state = State.REPORT_COMPLETE

            return ["Thank you for providing all the necessary information. Your report will be reviewed by our team."]
        else:
            return ["Invalid response, please type the number corresponding with the issue category."]

    def finish_report(self, message):
        if message.content == 'none':
            self.user_responses[UserResponse.SOURCE] = ""
        else:
            self.user_responses[UserResponse.SOURCE] = message.content
        self.state = State.REPORT_COMPLETE
        return ["Thank you for reporting and providing all the necessary information. Our content moderation team will review the message and decide on appropriate action. This may include post and/or account removal"]
    
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
        
    


    

