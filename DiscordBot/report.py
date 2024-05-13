from enum import Enum, auto
import discord
import re


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_INITIAL_REASON = auto()
    AWAITING_NUDITY_REASON = auto()
    AWAITING_MINOR_INVOLVEMENT_ANSWER = auto()
    AWAITING_MET_IN_PERSON_ANSWER = auto()
    AWAITING_EXPLANATION_INPUT = auto()
    AWAITING_NUDITY_EXPLANATION_INPUT = auto()
    AWAITING_FINAL_ADDITIONAL_INFORMATION = auto()
    AWAITING_BLOCK_ANSWER = auto()
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    EXPLANATION_INPUT_LIMIT = 300

    YES_NO_OPTIONS = [
        "Yes",
        "No"
    ]
    INITIAL_OPTIONS = [
        "Nudity or sexual activity",
        "Terrorism",
        "Harassment",
        "Hate Speech",
        "Spam",
        "Selling of illegal goods",
        "Something else"
    ]
    NUDITY_OPTIONS = [
        "They are threatening to share intimate pictures of me or someone else",
        "They sent me intimate images of themselves or of someone else",
        "They asked for intimate images of me or someone else",
        "Something else"
    ]

    REPORT_COMPLETE_OTHER_MESSAGE = "Thank you for helping us keep our community safe! We will investigate the matter and follow up as needed."
    REPORT_COMPLETE_SEXTORTION_MESSAGE = '''Thank you for helping us keep our community safe! We will investigate the matter and follow up as needed.
    Stop responding to their messages, but do not delete the chat.
    If someone is in danger, contact law enforcement immediately.
    You are not alone and it is not your fault this is happening.
    If you know or suspect intimate images of you or someone under 18 have been leaked, visit Take It Down (https://takeitdown.ncmec.org/) for help.
    Take care of yourself and loved ones. [link to platform's mental health resources]'''

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
            reply = "Thank you for starting the reporting process. "
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
            self.state = State.AWAITING_INITIAL_REASON

            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```",
                    self.create_options_list("Select the reason for reporting this message. Don't worry, the person you are reporting against won't know it was you.",
                                             self.INITIAL_OPTIONS)]

        if self.state == State.AWAITING_INITIAL_REASON:
            i = self.get_index(message, self.INITIAL_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                self.state = State.AWAITING_NUDITY_REASON
                reply = self.create_options_list("Please select which subtype of abuse happened:",
                                                 self.NUDITY_OPTIONS)
            elif i == 6:
                self.state = State.AWAITING_EXPLANATION_INPUT
                reply = f"Please tell us what happened ({self.EXPLANATION_INPUT_LIMIT} word limit)"
            else:
                self.state = State.AWAITING_FINAL_ADDITIONAL_INFORMATION
                reply = f"Please add any additional information you think is relevant ({self.EXPLANATION_INPUT_LIMIT} word limit)."
            return [reply]

        if self.state == State.AWAITING_NUDITY_REASON:
            i = self.get_index(message, self.NUDITY_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: give priority 1
                pass
            elif i == 1:
                # TODO: give priority 3
                pass
            elif i == 2:
                # TODO: give priority 2
                pass
            if i == 3:
                self.state = State.AWAITING_NUDITY_EXPLANATION_INPUT
                reply = f"Please tell us what happened ({self.EXPLANATION_INPUT_LIMIT} word limit)"
            else:
                self.state = State.AWAITING_MINOR_INVOLVEMENT_ANSWER
                reply = self.create_options_list("Does it involve someone under 18, either you or someone else?",
                                                 self.YES_NO_OPTIONS)
            return [reply]

        if self.state == State.AWAITING_MINOR_INVOLVEMENT_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: add yes to moderator report
                pass
            if i == 1:
                # TODO: add no to moderator report
                pass
            self.state = State.AWAITING_MET_IN_PERSON_ANSWER
            reply = self.create_options_list("Have you or the person you are reporting on behalf met them in person?",
                                             self.YES_NO_OPTIONS)
            return [reply]

        if self.state == State.AWAITING_MET_IN_PERSON_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: add yes to moderator report, give highest priority 1 if minor?
                pass
            if i == 1:
                # TODO: add no to moderator report
                pass
            self.state = State.AWAITING_FINAL_ADDITIONAL_INFORMATION
            reply = f"Please add any additional information you think is relevant ({self.EXPLANATION_INPUT_LIMIT} word limit)."
            return [reply]

        if self.state == State.AWAITING_EXPLANATION_INPUT:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                # TODO: attach explanation to moderator report
                self.state = State.AWAITING_FINAL_ADDITIONAL_INFORMATION
                reply = f"Please add any additional information you think is relevant ({self.EXPLANATION_INPUT_LIMIT} word limit)."
            return [reply]

        if self.state == State.AWAITING_NUDITY_EXPLANATION_INPUT:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                # TODO: attach explanation to moderator report
                self.state = State.AWAITING_MINOR_INVOLVEMENT_ANSWER
                reply = self.create_options_list("Does the abuse involve someone under 18, either you or someone else?",
                                                 self.YES_NO_OPTIONS)
            return [reply]

        if self.state == State.AWAITING_FINAL_ADDITIONAL_INFORMATION:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                self.state = State.AWAITING_BLOCK_ANSWER
                reply = [self.REPORT_COMPLETE_SEXTORTION_MESSAGE,
                         self.create_options_list("Would you like to block this account?",
                                                  self.YES_NO_OPTIONS)]
            return reply

        if self.state == State.AWAITING_BLOCK_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: yes, block account
                reply = "The account you've reported will be blocked. "
                pass
            # TODO: forward final report to moderator
            self.state = State.REPORT_COMPLETE
            reply += "Report complete."
            return [reply]

        return []

    def create_options_list(self, prompt, options):
        res = prompt
        for i, option in enumerate(options):
            res += f"\n\t{i}\. {option}"
        return res

    def get_index(self, message, options):
        try:
            i = int(message.content.strip())
        except:
            return -1
        if i not in range(len(options)):
            return -1
        return i

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
