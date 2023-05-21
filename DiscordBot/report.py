import re
from enum import Enum, auto

import discord


class State(Enum):
    # SECTION 0: START
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()

    # SECTION 1: USER DETAILS
    # Are you reporting on behalf of someone else?
    AWAITING_USER_DETAILS = auto()
    AWAITING_ON_BEHALF_OF = auto()

    # SECTION 2: REPORT DETAILS
    # Please select the reason for reporting this message
    AWAITING_REASON = auto()

    # Please select the type of abuse
    AWAITING_ABUSE_TYPE = auto()

    # Which of the following best describes the situation?
    AWAITING_ABUSE_DESCRIPTION = auto()

    # SECTION 2a: UNWANTED REQUESTS DETAILS
    # What is the account you are reporting requesting?
    AWAITING_UNWANTED_REQUESTS = auto()

    # Have you or the person on behalf of whom this report is being filed received multiple requests from the account you are reporting?
    AWAITING_MULTIPLE_REQUESTS = auto()
    AWAITING_APPROXIMATE_REQUESTS = auto()

    # Have you or the person on behalf of whom this report is being filed complied with these requests?
    AWAITING_COMPLIED_WITH_REQUESTS = auto()

    # SECTION 3: ADDITIONAL INFORMATION
    # Does the sexually explicit content involve a minor?
    AWAITING_MINOR_PARTICIPATION = auto()

    # Does this content contain you or the person on behalf of whom this report is being filed?
    AWAITING_CONTAIN_YOURSELF = auto()

    # Is the account you are reporting encouraging self-harm?
    AWAITING_ENCOURAGE_SELF_HARM = auto()

    # Would you like to provide any additional information?
    AWAITING_ADDITIONAL_INFO = auto()
    AWAITING_PLEASE_SPECIFY = auto()

    # SECTION X: FINAL STEPS
    # Would you like to block the account you have reported?
    AWAITING_BLOCK_USER = auto()

    # Please confirm that you would like to submit this report.
    AWAITING_CONFIRMATION = auto()

    # Thank you for reporting this activity.
    # Our moderation team will review your report and contact you if needed.
    # No further action is required on your part.
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORDS = ["yes", "y"]
    NO_KEYWORDS = ["no", "n"]

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

    async def handle_message(self, message):
        """
        This function makes up the meat of the user-side reporting flow. It defines how
        we transition between states and what prompts to offer at each of those states.
        You're welcome to change anything you want; this skeleton is just here to get
        you started and give you a model for working with Discord.
        """

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            self.state = State.AWAITING_MESSAGE
            return [
                (
                    "Thank you for starting the reporting process. Say `help` at any"
                    " time for more information."
                ),
                "Please copy paste the link to the message you want to report.",
                (
                    "You can obtain this link by right-clicking the message and"
                    " clicking `Copy Message Link`."
                ),
            ]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
            if not m:
                return [
                    "I'm sorry, I couldn't read that link. Please try again or say"
                    " `cancel` to cancel."
                ]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [
                    "I cannot accept reports of messages from guilds that I'm not in."
                    " Please have the guild owner add me to the guild and try again."
                ]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [
                    "It seems this channel was deleted or never existed. Please try"
                    " again or say `cancel` to cancel."
                ]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [
                    "It seems this message was deleted or never existed. Please try"
                    " again or say `cancel` to cancel."
                ]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            return [
                "I found this message:",
                "```" + message.author.name + ": " + message.content + "```",
                "Is this the message you want to report? Please say `yes` or `no`.",
            ]

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content.lower() in self.YES_KEYWORDS:
                self.state = State.AWAITING_USER_DETAILS
                # TODO: save the message for later
                return [
                    "Are you reporting on behalf of someone else? Please say `yes` or"
                    " `no`."
                ]
            elif message.content.lower() in self.NO_KEYWORDS:
                self.state = State.AWAITING_MESSAGE
                return ["Please copy the link to the message you want to report."]
            else:
                return [
                    "I'm sorry, I didn't understand that. Please say `yes` or `no`."
                ]

        if self.state == State.AWAITING_USER_DETAILS:
            if message.content.lower() in self.YES_KEYWORDS:
                self.state = State.AWAITING_ON_BEHALF_OF
                return ["Who are you reporting on behalf of?"]
            elif message.content.lower() in self.NO_KEYWORDS:
                self.state = State.AWAITING_REASON
                # TODO: indicate that the user is reporting on their own behalf
                return [
                    "Please select the reason for reporting this message. React to this"
                    " message with the corresponding emoji.\n:one: - Harassment /"
                    " Offensive Content \n:two: - Spam \n:three: - Immediate"
                    " danger\n:four: - Other"
                ]
            else:
                return [
                    "I'm sorry, I didn't understand that. Please say `yes` or `no`."
                ]

        if self.state == State.AWAITING_ON_BEHALF_OF:
            # TODO: indicate that the user is reporting on behalf of someone else
            self.state = State.AWAITING_REASON
            return [
                "Please select the reason for reporting this message. React to this"
                " message with the corresponding emoji.\n:one: - Harassment / Offensive"
                " Content \n:two: - Spam \n:three: - Immediate danger\n:four: - Other"
            ]

        if self.state == State.AWAITING_REASON:
            self.state = State.AWAITING_ABUSE_DESCRIPTION
            return []

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
