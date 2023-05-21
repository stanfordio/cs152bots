import re
from enum import Enum, auto

import discord
from messages import (
    GenericMessage,
    ReportDetailsMessage,
    ReportStartMessage,
    UserDetailsMessage,
)


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
    YES_KEYWORDS = {"yes", "y"}
    NO_KEYWORDS = {"no", "n"}

    REACT_STAGES = {State.AWAITING_REASON, State.AWAITING_ABUSE_TYPE}

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
            return GenericMessage.CANCELLED

        if self.state == State.REPORT_START:
            self.state = State.AWAITING_MESSAGE
            return [ReportStartMessage.START, ReportStartMessage.REQUEST_MSG]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
            if not m:
                return ReportStartMessage.INVALID_LINK
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ReportStartMessage.NOT_IN_GUILD
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ReportStartMessage.CHANNEL_DELETED
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ReportStartMessage.MESSAGE_DELETED

            self.state = State.MESSAGE_IDENTIFIED
            return ReportStartMessage.MESSAGE_IDENTIFIED.format(
                author=message.author.name, content=message.content
            )

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content.lower() in self.YES_KEYWORDS:
                self.state = State.AWAITING_USER_DETAILS
                # TODO: save the message for later
                return UserDetailsMessage.ON_BEHALF_OF
            elif message.content.lower() in self.NO_KEYWORDS:
                self.state = State.AWAITING_MESSAGE
                return ReportStartMessage.REQUEST_MSG
            else:
                return GenericMessage.INVALID_YES_NO

        if self.state == State.AWAITING_USER_DETAILS:
            if message.content.lower() in self.YES_KEYWORDS:
                self.state = State.AWAITING_ON_BEHALF_OF
                return UserDetailsMessage.WHO_ON_BEHALF_OF
            elif message.content.lower() in self.NO_KEYWORDS:
                # TODO: indicate that the user is reporting on their own behalf
                self.state = State.AWAITING_REASON
            else:
                return GenericMessage.INVALID_YES_NO

        if self.state == State.AWAITING_ON_BEHALF_OF:
            # TODO: indicate that the user is reporting on behalf of someone else
            self.state = State.AWAITING_REASON

        # Reaction must be added to this message before continuing
        if self.state == State.AWAITING_REASON:
            return ReportDetailsMessage.REASON_FOR_REPORT

        if self.state == State.AWAITING_ABUSE_TYPE:
            return ReportDetailsMessage.ABUSE_TYPE

        return []

    def handle_reaction_add(self, emoji: discord.PartialEmoji):
        """
        This function handles reactions to the message that the bot sends.
        """
        # Reaction was added to a message that didn't require a reaction
        if self.state not in self.REACT_STAGES:
            return []

        if self.state == State.AWAITING_REASON:
            if str(emoji.name) not in {"1️⃣", "2️⃣", "3️⃣", "4️⃣"}:
                return [
                    GenericMessage.INVALID_REACTION,
                    ReportDetailsMessage.REASON_FOR_REPORT,
                ]
            else:
                # TODO: save the reason for later
                self.state = State.AWAITING_ABUSE_TYPE
                return ReportDetailsMessage.ABUSE_TYPE

        if self.state == State.AWAITING_ABUSE_TYPE:
            if str(emoji.name) not in {"1️⃣", "2️⃣", "3️⃣", "4️⃣"}:
                return [
                    GenericMessage.INVALID_REACTION,
                    ReportDetailsMessage.ABUSE_TYPE,
                ]
            else:
                # TODO: save the abuse type for later
                self.state = State.AWAITING_ABUSE_DESCRIPTION
                # return ReportDetailsMessage.ABUSE_DESCRIPTION

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
