import re
from datetime import datetime
from enum import Enum, auto
from typing import List

import discord
from data import ReportData
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

    # SECTION 4: FINAL STEPS
    # Would you like to block the account you have reported?
    AWAITING_BLOCK_USER = auto()

    # Please confirm that you would like to submit this report.
    AWAITING_CONFIRMATION = auto()

    # Thank you for reporting this activity.
    # Our moderation team will review your report and contact you if needed.
    # No further action is required on your part.
    REPORT_COMPLETE = auto()


class Moderate:
    LIST_KEYWORD = "list"
    START_KEYWORD = "handle"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORDS = {"yes", "y"}
    NO_KEYWORDS = {"no", "n"}
    SKIP_KEYWORD = "skip"

    REACT_STAGES = {
        State.AWAITING_REASON,
        State.AWAITING_ABUSE_TYPE,
        State.AWAITING_ABUSE_DESCRIPTION,
        State.AWAITING_UNWANTED_REQUESTS,
    }

    # keys are stages that can be skipped, values are the next stage to skip to & message for next stage
    SKIP_STAGES = {
        State.AWAITING_ENCOURAGE_SELF_HARM: [
            State.AWAITING_ADDITIONAL_INFO,
            ReportDetailsMessage.ADDITIONAL_INFO,
        ]
    }

    def __init__(self, client: discord.Client) -> None:
        self.state = State.REPORT_START
        self.client = client
        self.data = ReportData()
        self.curr_report = None

    async def handle_message(self, message: discord.Message) -> List[str]:
        """
        This function makes up the meat of the moderator-side reporting flow. reports only on
        setortion violations.
        """
        
        if message.content == self.SKIP_KEYWORD:
            if self.state in self.SKIP_STAGES:
                prev_state = self.state
                self.state = self.SKIP_STAGES[prev_state][0]
                return self.SKIP_STAGES[prev_state][1]
            else:
                return GenericMessage.INVALID_SKIP

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return GenericMessage.CANCELED

        if self.state == State.REPORT_START:
            self.data.reporter = message.author
            self.state = State.AWAITING_MESSAGE
            return [ReportStartMessage.START, ReportStartMessage.MODERATE_REQUEST]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = message.content
            found_report = None
            accused = ""
            for r in self.client.open_reports:
                if m == r.id:
                    found_report = r


            print(found_report)
            print(found_report.message.author.name)

            print("report: ", found_report.summary)
            
            self.curr_report = found_report
            if not found_report:
                return ReportStartMessage.INVALID_REPORTID
            #guild = self.client.get_guild(int(m.group(1)))
            #if not guild:
                #return ReportStartMessage.NOT_IN_GUILD
            #channel = guild.get_channel(int(m.group(2)))
           #if not channel:
                #return ReportStartMessage.CHANNEL_DELETED
            #try:
                #message = await channel.fetch_message(int(m.group(3)))
            #except discord.errors.NotFound:
                #return ReportStartMessage.MESSAGE_DELETED

            self.state = State.MESSAGE_IDENTIFIED

            # save the message for later
            self.data.message = message

            return ReportStartMessage.REPORT_IDENTIFIED.format(
                report_id=m, content=found_report.message.author.name
            )

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content.lower() in self.YES_KEYWORDS:
                self.state = State.AWAITING_ABUSE_TYPE
                print("curr report", self.curr_report.summary)
                await message.channel.send(self.curr_report.summary)
                return ReportDetailsMessage.MODERATOR_ABUSE_TYPE
            elif message.content.lower() in self.NO_KEYWORDS:
                self.state = State.AWAITING_MESSAGE
                return ReportStartMessage.REQUEST_MSG
            else:
                return GenericMessage.INVALID_YES_NO


        if self.state == State.AWAITING_ABUSE_TYPE:
            if message.content.lower() in self.YES_KEYWORDS:
                self.data.abuse_type = "Sexually explicit harassment"
                response = []
                self.data.blocked_user = True
                response.append(
                    ReportDetailsMessage.BLOCKED.format(
                        author=self.curr_report.message.author.name
                    )
                )
                self.state = State.AWAITING_CONFIRMATION
                response.extend(
                    [self.data.user_summary, ReportDetailsMessage.CONFIRMATION]
                )
                return response
                
            elif message.content.lower() in self.NO_KEYWORDS:
                #investigate for adversarial reporting
                self.state = State.REPORT_COMPLETE
                self.state = State.AWAITING_CONFIRMATION
                response.extend(
                    [self.data.user_summary, ReportDetailsMessage.CONFIRMATION]
                )
                return response
                
            else:
                return GenericMessage.INVALID_YES_NO

        if self.state == State.AWAITING_CONFIRMATION:
            if message.content.lower() in self.YES_KEYWORDS:
                self.data.report_completed_at = datetime.utcnow()

                # Send the report to the mod channel
                await self.client.send_to_mod_channels(self.data.moderator_summary)
                self.client.open_reports.append(self.data)

                self.state = State.REPORT_COMPLETE
                return GenericMessage.REPORT_COMPLETE
            elif message.content.lower() in self.NO_KEYWORDS:
                # TODO: what do we do if they say no...?
                return "****TODO****???" + GenericMessage.CANCELED
            else:
                return GenericMessage.INVALID_YES_NO

        return []

       

    def moderation_complete(self):
        return self.state == State.REPORT_COMPLETE
