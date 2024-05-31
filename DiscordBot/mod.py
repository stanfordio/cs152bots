from enum import Enum, auto
import discord
import re

class State(Enum):
    MOD_START = auto()
    DANGER = auto()
    HATE_SPEECH = auto()
    SEVERITY = auto()
    FALSIFIED = auto()
    FLAG = auto()
    TERRORISM = auto()
    REPEAT_TERRORISM = auto()
    FINAL_MESSAGE = auto()

class Mod:
    START_KEYWORD = "mod"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.MOD_START
        self.client = client
        self.message = None
        self.report_type = None
        self.sub_type = None
        self.reported_message = None

    async def handle_message(self, message, mod_channel):
        '''
        This function manages the state transitions and user interactions for the reporting process in a Discord bot.
        '''
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.FINAL_MESSAGE
            return ["Moderation flow cancelled."]

        if self.state == State.MOD_START:
            reply = "Thank you for starting the moderation process. Say `help` at any time for more information.\n\n"
            reply += "Is there imminent danger? State 'Yes' or 'No'."
            self.state = State.DANGER
            return [reply]
        
        if self.state == State.DANGER:
            if message.content.lower() != "yes" and message.content.lower() != "no":
                return ["Invalid selection. Please try again."]
            elif message.content.lower() == "yes":
                self.state = State.SEVERITY
                reply = "This has been classified as a high priority message. \n\n"
                reply += "Please classify this message in terms of severity: 'Low', 'Medium', 'High'"
                return [reply]
            else:
                self.state = State.HATE_SPEECH
                return ["Is this an instance of hate speech? State 'Yes' or 'No'."]

        if self.state == State.HATE_SPEECH:
            if message.content.lower() != "yes" and message.content.lower() != "no":
                return ["Invalid selection. Please try again."]
            self.state = State.SEVERITY
            if message.content.lower() == "yes":
                reply = "This has been classified as a high priority message. \n\n"
                reply += "Please classify this message in terms of severity: 'Low', 'Medium', 'High'"
                return [reply]
            else:
                reply = "This has been classified as a lower priority message. \n\n"
                reply += "Please classify this message in terms of severity: 'Low', 'Medium', 'High'"
                return [reply]

        if self.state == State.SEVERITY:
            severity = message.content.strip().lower()
            if severity == "low":
                reply = "Is this a false report? State 'Yes' or 'No'."
                self.state = State.FALSIFIED
                return [reply]
            elif severity == "medium":
                reply = "Has this user been flagged for posting offensive content over 5 times this month? State 'Yes' or 'No'."
                self.state = State.FLAG
                return [reply]
            elif severity == "high":
                reply = "Is this content related to terrorism? State 'Yes' or 'No'."
                self.state = State.TERRORISM
                return [reply]
            else:
                return ["Invalid selection. Please try again."]
        
        if self.state == State.FALSIFIED:
            falsified = message.content.strip().lower()
            if falsified == "yes":
                self.state = State.FINAL_MESSAGE
                reply = "If this user has reported 5 or more false reports, we will temporarily suspend their account. \n\n"
                reply += "Otherwise, we will ask them to please ensure that future reports are correctly classified to avoid account suspension."
                return [reply]
            elif falsified == "no":
                self.state = State.FINAL_MESSAGE
                reply = "It looks like this was a minor incident. No action taken at this time."
                return [reply]
            else:
                return ["Invalid selection. Please try again."]

        if self.state == State.FLAG:
            flag = message.content.strip().lower()
            if flag == "yes":
                self.state = State.FINAL_MESSAGE
                reply = "We have temporarily suspended the user's account for many reports of content that violate community guidelines. No further action is necessary."
                return [reply]
            elif flag == "no":
                self.state = State.FINAL_MESSAGE
                reply = "We have notified the user to please refrain from posting content that violates community guidelines. No further action is necessary."
                return [reply]
            else:
                return ["Invalid selection. Please try again."]

        if self.state == State.TERRORISM:
            terror = message.content.strip().lower()
            if terror == "yes":
                reply = "We have deleted this content, flagged the user, and issued them a warning. \n\n"
                reply += "We will report this content to the FBI and local law enforcement and add the content to the GIFCT Database.\n\n"
                reply += "Has the user been flagged for terrorism content multiple times by multiple users? State 'Yes' or 'No'."
                self.state = State.REPEAT_TERRORISM
                return [reply]
            elif terror == "no":
                self.state = State.FLAG
                return ["Has this user been flagged for posting offensive content over 5 times this month? State 'Yes' or 'No'."]
            else:
                return ["Invalid selection. Please try again."]
        
        if self.state == State.REPEAT_TERRORISM:
            repeat = message.content.strip().lower()
            if repeat == "yes":
                self.state = State.FINAL_MESSAGE
                reply = "We are decrypting the user's account to flag their social network and deleting their account."
                return [reply]
            elif repeat == "no":
                self.state = State.FINAL_MESSAGE
                reply = "We have notified the user to please refrain from posting content that violates community guidelines. No further action is necessary."
                return [reply]
            else:
                return ["Invalid selection. Please try again."]

        if self.state == State.FINAL_MESSAGE:
            return ["Thank you!"]
        
        return []

    def report_complete(self):
        return self.state == State.FINAL_MESSAGE