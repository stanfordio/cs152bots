from enum import Enum, auto
import discord
import re
from discord.ext.context import ctx
from question_templates.block_or_mute import BlockOrMute, BlockOrMuteType
from question_templates.checking_spam import CheckingSpam, SpamRequestType
from question_templates.report_reason import ReportReason, ReportType


class ModerationRequest():
    block_or_mute: BlockOrMuteType = None
    spam_request: SpamRequestType = None
    report_type: ReportType = None

    def __init__(self, message):
        self.message_author = message.author.name
        self.message_content = message.content

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    BLOCK = auto()
    IS_SPAM = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        # TODO: Change back to report start
        self.state = State.MESSAGE_IDENTIFIED
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
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```"]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            # 30 second timeout wait
            report_reason = ReportReason(timeout=30)

            message = await ctx.channel.send(view=report_reason)

            report_reason.message = message
            # Here we wait for the ReportReason class to wait for users button press
            await report_reason.wait()

            if report_reason.report_type == None:
                self.state = State.REPORT_START
            elif report_reason.report_type == ReportType.OTHER:
                self.state = State.BLOCK
            elif report_reason.report_type == ReportType.SPAM:
                self.state = State.IS_SPAM
            elif report_reason.report_type == ReportType.POSSIBLE_SCAM:
                self.state = State.BLOCK
            else:
                self.state = State.REPORT_COMPLETE

        if self.state == State.IS_SPAM:
            await ctx.channel.send("Is this user asking you for something?")

            checking_spam = CheckingSpam(timeout=30)

            msg = await ctx.channel.send(view=checking_spam)

            checking_spam.message = msg

            await checking_spam.wait()

            #TODO: Check return value of class

            self.state = State.BLOCK


        if self.state == State.BLOCK:
            await ctx.channel.send("Would you like to block or mute this user?")

            block_or_mute = BlockOrMute(timeout=30)

            msg = await ctx.channel.send(view=block_or_mute)

            block_or_mute.message = msg

            await block_or_mute.wait()

            #TODO: Check return value of class

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

