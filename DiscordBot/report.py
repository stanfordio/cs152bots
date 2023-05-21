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
    USER_DETAILS_IDENTIFIED = auto()

    # SECTION 2: REPORT DETAILS
    # Please select the reason for reporting this message
    AWAITING_REASON = auto()
    HARRASSMENT_REASON_IDENTIFIED = auto() # -> REPORT_COMPLETE

    # Please select the type of abuse
    AWAITING_ABUSE_TYPE = auto()
    SEXUALLY_EXPLICIT_ABUSE_TYPE_IDENTIFIED = auto() # -> REPORT_COMPLETE

    # Which of the following best describes the situation?
    AWAITING_ABUSE_DESCRIPTION = auto()

    # SECTION 2a: UNWANTED REQUESTS DETAILS
    # What is the account you are reporting requesting?
    AWAITING_UNWANTED_REQUESTS = auto()
    UNWANTED_REQUESTS_IDENTIFIED = auto()

    # Have you or the person on behalf of whom this report is being filed received multiple requests from the account you are reporting?
    AWAITING_MULTIPLE_REQUESTS = auto()
    AWAITING_APPROXIMATE_REQUESTS = auto()
    MULTIPLE_REQUESTS_IDENTIFIED = auto()

    # Have you or the person on behalf of whom this report is being filed complied with these requests?
    AWAITING_COMPLIED_WITH_REQUESTS = auto()

    ABUSE_DESCRIPTION_IDENTIFIED = auto()

    # SECTION 3: ADDITIONAL INFORMATION
    # Does the sexually explicit content involve a minor?
    AWAITING_MINOR_PARTICIPATION = auto()
    MINOR_PARTICIPATION_IDENTIFIED = auto()

    # Does this content contain you or the person on behalf of whom this report is being filed?
    AWAITING_CONTAIN_YOURSELF = auto()
    CONTAIN_YOURSELF_IDENTIFIED = auto()

    # Is the account you are reporting encouraging self-harm?
    AWAITING_ENCOURAGE_SELF_HARM = auto()
    ENCOURAGE_SELF_HARM_IDENTIFIED = auto()

    # Would you like to provide any additional information?
    AWAITING_ADDITIONAL_INFO = auto()
    AWAITING_PLEASE_SPECIFY = auto()
    ADDITIONAL_INFO_IDENTIFIED = auto()

    # SECTION X: FINAL STEPS
    # Would you like to block the account you have reported?
    AWAITING_BLOCK_USER = auto()
    BLOCK_USER_IDENTIFIED = auto()
    
    # Please confirm that you would like to submit this report.
    AWAITING_CONFIRMATION = auto()
    CONFIRMATION_IDENTIFIED = auto()

    # Thank you for reporting this activity.
    # Our moderation team will review your report and contact you if needed.
    # No further action is required on your part.
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

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
                (
                    "This is all I know how to do right now - it's up to you to build"
                    " out the rest of my reporting flow!"
                ),
            ]

        if self.state == State.MESSAGE_IDENTIFIED:
            return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
