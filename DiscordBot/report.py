from enum import Enum, auto
import discord
import re
from discord.ext.context import ctx
from question_templates.block_or_mute import BlockOrMute, BlockOrMuteType
from question_templates.checking_scam import CheckingScam, ScamRequestType
from question_templates.report_reason import ReportReason, ReportType
from message_util import next_message


# TODO: Add logic to this class for keeping track of score
#class ModerationRequest():
    #block_or_mute: BlockOrMuteType = None
    #scam_request: ScamRequestType = None
    #report_type: ReportType = None

    #def __init__(self, message):
        #self.message_author = message.author.name
        #self.message_content = message.content

    #def return_report():

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    BLOCK = auto()
    IS_SCAM = auto()
    REPORT_COMPLETE = auto()
    REPORT_CANCELED = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        # TODO: Change back to report start
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            await ctx.channel.send(''.join(reply))

            wait_for_message = True
            while (wait_for_message):
                msg = await next_message()
                if not msg or msg.content == self.CANCEL_KEYWORD:
                    self.state == self.CANCEL_KEYWORD
                    return
                # Parse out the three ID strings from the message link
                m = re.search('/(\d+)/(\d+)/(\d+)', msg.content)
                if not m:
                    await ctx.channel.send("I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel.")
                    continue
                guild = self.client.get_guild(int(m.group(1)))
                if not guild:
                    await ctx.channel.send("I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again.")
                    continue
                channel = guild.get_channel(int(m.group(2)))
                if not channel:
                    await ctx.channel.send("It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel.")
                    continue
                try:
                    message = await channel.fetch_message(int(m.group(3)))
                    #TODO: Add message to our report
                    await ctx.channel.send(''.join(["I found this message:", "```" + message.author.name + ": " + message.content + "```"]))
                    wait_for_message = False
                except discord.errors.NotFound:
                    await ctx.channel.send("It seems this message was deleted or never existed.")

            self.state = State.MESSAGE_IDENTIFIED
        
        if self.state == State.MESSAGE_IDENTIFIED:
            await ctx.channel.send("Please choose a reason for you report.")
            # 30 second timeout wait
            report_reason = ReportReason(timeout=30)

            message = await ctx.channel.send(view=report_reason)

            report_reason.message = message
            # Here we wait for the ReportReason class to wait for users button press
            await report_reason.wait()

            if report_reason.report_type == None:
                self.state = State.REPORT_CANCELED
            elif report_reason.report_type == ReportType.CANCEL:
                self.state = State.REPORT_CANCELED
            elif report_reason.report_type == ReportType.OTHER:
                self.state = State.BLOCK
            elif report_reason.report_type == ReportType.SCAM:
                self.state = State.IS_SCAM
            elif report_reason.report_type == ReportType.SPAM:
                self.state = State.BLOCK
            else:
                self.state = State.REPORT_COMPLETE

        if self.state == State.IS_SCAM:
            await ctx.channel.send("Is this user asking you for something?")

            checking_scam = CheckingScam(timeout=30)

            msg = await ctx.channel.send(view=checking_scam)

            checking_scam.message = msg

            res = await checking_scam.wait()

            if checking_scam.scam_type == None or checking_scam.scam_type == ScamRequestType.CANCEL:
                self.state = State.REPORT_CANCELED
            else:
                self.state = State.BLOCK

        if self.state == State.BLOCK:
            await ctx.channel.send("Would you like to block or mute this user?")
            print("entered is block")
            block_or_mute = BlockOrMute(timeout=30)

            msg = await ctx.channel.send(view=block_or_mute)

            block_or_mute.message = msg

            await block_or_mute.wait()

            self.state = State.REPORT_COMPLETE

            #TODO: Check return value of class
            #if block_or_mute.requested_response_type == BlockOrMuteType.BLOCK:
            # TODO: In this case we would add that the users requesting blocking someone to the report

        # TODO: Return our completed report class
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE or self.state == State.REPORT_CANCELED
    


    

