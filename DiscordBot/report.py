from enum import Enum, auto
import discord
import re
from user_report import (
    StartView,
    MoreInfoView,
    SUBMIT_MSG,
    ABUSE_TYPES,
    HARASSMENT_TYPES,
)
from typing import Optional, List


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    IN_VIEW = auto()
    GETTING_MSG_ID = auto()
    GETTING_EXTRA_INFO = auto()
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        # State to handle inner working of bot
        self.state = State.REPORT_START
        self.client = client
        # State for filing a report
        self.message = None
        self.abuse_type: Optional[ABUSE_TYPES] = None
        self.harassment_types: List[HARASSMENT_TYPES] = []
        self.target = None  # TODO: Still has to change
        self.additional_msgs: List[str] = None
        self.additional_info: Optional[str] = None

    async def handle_message(self, message):
        """
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        """

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
            m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
            if not m:
                return [
                    "I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."
                ]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [
                    "I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."
                ]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [
                    "It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."
                ]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [
                    "It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."
                ]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.IN_VIEW
            self.message = message
            return [
                "I found this message:",
                "```" + message.author.name + ": " + message.content + "```",
                ("Why would you like to report this message?", StartView(report=self)),
            ]

        if self.state == State.GETTING_MSG_ID:
            # TODO: refactor
            # Parse out the three ID strings from the message link
            m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
            if not m:
                return [
                    "I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."
                ]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [
                    "I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."
                ]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [
                    "It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."
                ]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [
                    "It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."
                ]
            self.additional_msgs.append(message)
            self.state = State.IN_VIEW
            return [
                "I found this message to add to the report:",
                "```" + message.author.name + ": " + message.content + "```",
                (
                    "Is there another message you would like to add to this report?",
                    MoreInfoView(report=self),
                ),
            ]

        if self.state == State.GETTING_EXTRA_INFO:
            self.additional_info = message.content
            self.state = State.REPORT_COMPLETE
            return [SUBMIT_MSG]

        if self.state == State.IN_VIEW:
            # If there is a view, the view should be interacted with.
            return [
                "Sorry, you are in the middle of a report.\nContinue by selecting an option above or stop by typing `cancel`."
            ]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def report_info(self):
        return f"Reported Message:\n```{self.message.author.name}: {self.message.content}```\nAbuse Type: {self.abuse_type}\nHarassment Types: {self.harassment_types}\nTarget: {self.target} \nAdditional Msgs: {self.additional_msgs}\nAdditional Info {self.additional_info}"

    # State setters and getters
    def set_info_state(self):
        self.state = State.GETTING_EXTRA_INFO

    def set_msg_id_state(self):
        self.state = State.GETTING_MSG_ID

    def set_report_done(self):
        self.state = State.REPORT_COMPLETE

    def set_abuse_type(self, abuse: ABUSE_TYPES):
        self.abuse_type = abuse

    def set_harassment_types(self, harassments: HARASSMENT_TYPES):
        self.harassment_types = harassments

    def set_target(self, target):
        self.target = target
