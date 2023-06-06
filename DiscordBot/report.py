from enum import Enum, auto
import discord
import re
from discord.ext.context import ctx
from question_templates.block_or_mute import BlockOrMute, BlockOrMuteType
from question_templates.checking_scam import CheckingScam, ScamRequestType
from question_templates.report_reason import ReportReason, ReportType
from question_templates.impersonation import Impersonation, ImpersonationType
from question_templates.possible_impersonation import PossibleImpersonation, IsImpersonation
from message_util import next_message


class ModerationRequest():
    block_or_mute: BlockOrMuteType = None
    scam_request: ScamRequestType = None
    impersonation: ImpersonationType = None
    is_impersonating: IsImpersonation = None
    report_type: ReportType = None
    score: int = 0

    def __init__(self, message):
        self.message = message

    def increment_score(self):
        self.score += 1
    
    def print_report(self):
        print_str = "Moderation Report:\n"
        print_str += "Author: " + self.message.author.name + "\n"
        print_str += "Message: " + self.message.content + "\n"
        print_str += "Score: " + str(self.score) + "\n"
        print_str += "Report Type: " + str(self.report_type) + "\n"

        if self.block_or_mute:
            print_str += "Block/Mute Type: " + str(self.block_or_mute) + "\n"

        if self.scam_request:
            print_str += "Scam Request Type: " + str(self.scam_request) + "\n"

        if self.impersonation:
            print_str += "Impersonation Type: " + str(self.impersonation) + "\n"

        if self.is_impersonating:
            print_str += "Is Impersonating: " + str(self.is_impersonating) + "\n"

        return print_str
class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    BLOCK = auto()
    SPAM = auto()
    POSSIBLE_IMP = auto()
    IMPERSONATION = auto()
    REPORT_COMPLETE = auto()
    REPORT_CANCELED = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report = None
    
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
                    self.state = self.CANCEL_KEYWORD
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
                    #TODO(: Add message to our report
                    self.report = ModerationRequest(message)
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

            # Update our internal report
            self.report.report_type = report_reason.report_type

            if report_reason.report_type == None:
                self.state = State.REPORT_CANCELED
            elif report_reason.report_type == ReportType.CANCEL:
                await ctx.channel.send("Report Canceled")
                self.state = State.REPORT_COMPLETE
            elif report_reason.report_type == ReportType.OTHER:
                self.state = State.BLOCK
            elif report_reason.report_type == ReportType.SCAM:
                self.report.increment_score()
                self.state = State.POSSIBLE_IMP
            elif report_reason.report_type == ReportType.SPAM:
                self.state = State.SPAM
            else:
                self.state = State.REPORT_COMPLETE

        if self.state == State.POSSIBLE_IMP:
            await ctx.channel.send("Is this user impersonating someone?")

            check_if_impersonation = PossibleImpersonation(timeout=45)
            
            msg = await ctx.channel.send(view=check_if_impersonation)

            check_if_impersonation.message = msg

            await check_if_impersonation.wait()
            
            self.report.is_impersonating = check_if_impersonation.is_impersonating

            if  check_if_impersonation.is_impersonating == IsImpersonation.YES:
                self.report.increment_score()
                self.state = State.IMPERSONATION
            elif check_if_impersonation.is_impersonating == IsImpersonation.NO:
                self.state = State.SPAM
            else:
                await ctx.channel.send("Report Canceled")
                self.state = State.REPORT_CANCELED


        if self.state == State.IMPERSONATION:
            await ctx.channel.send("Thank you for notifying us. Our team will review this message and account. If you'd like more information, please describe who this user is impersonating.")

            impersonator = Impersonation(timeout=45) 

            msg = await ctx.channel.send(view=impersonator)

            impersonator.message = msg

            await impersonator.wait()

            if impersonator.impersonation_type == ImpersonationType.CANCEL:
                await ctx.channel.send("Report Canceled")
                self.state = State.REPORT_CANCELED
            else:
                self.report.impersonation = impersonator.impersonation_type
                self.state = State.SPAM

        if self.state == State.SPAM:
            await ctx.channel.send("Is this user asking you for something?")

            checking_scam = CheckingScam(timeout=30)

            msg = await ctx.channel.send(view=checking_scam)

            checking_scam.message = msg

            res = await checking_scam.wait()

            self.report.scam_request = checking_scam.scam_type

            if checking_scam.scam_type == ScamRequestType.CANCEL:
                await ctx.channel.send("Report Canceled")
                self.state = State.REPORT_CANCELED
            # User didn't ask for anything
            elif checking_scam.scam_type == ScamRequestType.NONE:
                self.state = State.BLOCK
            else:
                self.report.increment_score()
                self.state = State.BLOCK

        if self.state == State.BLOCK:
            await ctx.channel.send("Would you like to block or mute this user?")
            print("entered is block")
            block_or_mute = BlockOrMute(timeout=30)

            msg = await ctx.channel.send(view=block_or_mute)

            block_or_mute.message = msg

            await block_or_mute.wait()

            if block_or_mute.requested_response_type == BlockOrMuteType.CANCEL:
                await ctx.channel.send("Report Canceled")
                self.state = State.REPORT_CANCELED
            else:
                self.report.block_or_mute = block_or_mute.requested_response_type
                self.state = State.REPORT_COMPLETE

        return self.report

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE or self.state == State.REPORT_CANCELED

    def report_canceled(self):
        return self.state == State.REPORT_CANCELED
    


    

