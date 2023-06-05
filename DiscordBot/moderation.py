
from enum import Enum, auto
import discord
import re
from discord.ext.context import ctx
from message_util import next_message
from report import ModerationRequest 
from question_templates.reliable_report import ReportIsReliable, ReportReliability

class State(Enum):
   START = auto() 
   UNKNOWN_FAITH = auto()
   GOOD_FAITH = auto()
   BAD_FAITH = auto()
   TIMED_OUT = auto()
   COMPLETE = auto()

class Moderation_Flow:

    def __init__(self, message, mod_channel, automated=False):
        if automated:
            self.state = State.GOOD_FAITH
        else:
            self.state = State.UNKNOWN_FAITH
        self.mod_channel = mod_channel
        self.message = message
    
    async def handle_moderation_report(self):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if self.state == State.UNKNOWN_FAITH:
            await self.mod_channel.send("Did the user accurately follow the user reporting flow?")

            report_is_reliable = ReportIsReliable(timeout=200)

            msg = await self.mod_channel.send(view=report_is_reliable)

            report_is_reliable.message = msg

            await report_is_reliable.wait()

            if report_is_reliable.report_reliability == ReportReliability.GOOD:
                self.state = State.GOOD_FAITH
            elif report_is_reliable.report_reliability == ReportReliability.BAD:
                self.state = State.BAD_FAITH
            else:
                self.state = State.TIMED_OUT
            
        if self.state == State.BAD_FAITH:
            await self.mod_channel.send("Checking the total number of bad faith reports submitted by this user")
            #TODO: Keep track of total number of bad faith reports based on message.author.id, so keep a database in a csv file or some datastruct like a map
            self.send_banning_message(1)
            return

        if self.state == State.GOOD_FAITH:
            await self.mod_channel.send("Who does the alleged scammer claim to be?")
            #TODO: Create a class to collect this information similar to impersonation.py then save to database




    async def send_banning_message(self, ban_length):
        await self.message.author.send("You have been banned for " + str(ban_length) + " days.")

    async def send_permanent_banning_message(self):
        await self.message.author.send("You have been banned from using this platform")

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE or self.state == State.REPORT_CANCELED

    def report_cancled(self):
        return self.state == State.REPORT_CANCELED