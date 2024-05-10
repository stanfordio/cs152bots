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
    AWAITING_MORE_INFORMATION = auto()
    AWAITING_SOURCE = auto()
    AWAITING_NOTE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    
    # Continue or not continue with messages
    YES_KEYWORD = "y"
    NO_KEYWORD = "n"

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
            return self.handle_message_link(message)

        if self.state == State.MESSAGE_IDENTIFIED:
            return self.request_issue_category()

        elif self.state == State.AWAITING_ISSUE_CATEGORY:
            return self.request_specific_issue(message)

        elif self.state == State.AWAITING_SPECIFIC_ISSUE:
            return self.request_additional_info(message)

        elif self.state == State.AWAITING_MORE_INFORMATION:
            return self.request_source(message)

        elif self.state == State.AWAITING_SOURCE:
            return self.request_final_note(message)

        elif self.state == State.AWAITING_NOTE:
            self.state = State.REPORT_COMPLETE
            return ["Thank you for your report. It has been filed for further review."]
        
        return []

    def handle_message_link(self, message):
        m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
        if not m:
            return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
        # This is a stub for fetching a message, which would require Discord API calls.
        self.state = State.MESSAGE_IDENTIFIED
        return ["Message link processed successfully. Please select the issue category from the following options: inappropriate content, misleading information, or others."]

    def request_issue_category(self):
        reply =  "Please select the category that best describes your report:\n"
        reply += "1. Inappropriate Adult Content\n"
        reply += "2. Nudity and sexual content\n"
        reply += "3. Adult products and services\n"
        reply += "4. Sensitive content\n"
        reply += "5. Misleading or false information\n"
        reply += "6. Political disinformation"
        self.state = State.AWAITING_ISSUE_CATEGORY
        return [reply]

    def request_specific_issue(self, message):
        # Here you could parse the user's input to determine if it's valid
        self.state = State.AWAITING_MORE_INFORMATION
        return ["Thank you. Please provide more detailed information about the issue or any source to disprove the ad content."]

    def request_additional_info(self, message):
        # Assume the user has typed their explanation or said "none"
        self.state = State.AWAITING_SOURCE
        return ["Please provide any sources you might have that could help disprove or explain the issue with the ad. Type 'none' if you don't have any."]

    def request_source(self, message):
        # Assume the user has typed a source or said "none"
        self.state = State.AWAITING_NOTE
        return ["Lastly, please provide a written note with any additional details or your personal remarks. Type 'done' when you finish."]

    def request_final_note(self, message):
        # Assume the user has typed a final note or said "done"
        self.state = State.REPORT_COMPLETE
        return ["Thank you for providing all the necessary information. Your report will be reviewed by our team."]
    
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
        
    


    

