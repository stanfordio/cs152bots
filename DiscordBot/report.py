from enum import Enum, auto
import discord
import re

start_dialogue = "Please select a report reason"
start_options = [start_dialogue, "Spam", "Fake Account", "Harassment or Bullying", "Posting inappropriate things", "Scam", "Something else"]
scam_dialogue = "What is your reason for suspicion?"
scam_options = [scam_dialogue, "Fake Account", "Unrelated to the discord channel or anything that I've said", "Other reason, please specify"]
fake_account_dialogue = "Who is this person impersonating?"
fake_account_options = [fake_account_dialogue, "Pretending to be me", "Pretending to be someone I know", "Pretending to be a celebrity or public figure", "Pretending to be a business or organization"]
post_dialogue = "Select type of content this person is posting"
post_options = [post_dialogue, "Hate speech", "Adult nudity and sexual activity", "Child sexual exploitation, abuse, and nudity", "Violence and graphic content"]
scam_dialogue = "What did the user do?"
scam_options = [scam_dialogue, "Presented a suspicious investment opportunity", "Asked for password or other sensitive information", "Asked for money, even though we have never met", "User disappeared after money transaction", "Other [Please provide more details]"]
else_dialogue = "Please provide detailed descriptions"
else_options = [else_dialogue, "[Optional] Please attach any relevant screenshots that can help us investigate the issue."]
thanks_dialogue = "Thanks for reporting. Our content moderation team will review the profile and decide on the appropriate actions."
block_dialogue = "Would you like to block this user?"
final_options = [thanks_dialogue, block_dialogue, "yes", "no"]

class ReportState(Enum):
    Start = auto()
    Spam = auto()
    Fake = auto()
    Bully = auto()
    Post = auto()
    Scam = auto()
    Else = auto()
    Thanks = auto()
    End = auto()

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.flow_state = None
        self.reponses = []
    
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
            self.message == message
            self.flow_state = ReportState.Start
            return [start_options]
            # return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #         "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if self.flow_state == None:
                self.flow_state = ReportState.Start
                return [start_options]
            
            # Log the repsonses for later use
            self.responses.append(message)

            content = message.content.lower()
            if self.flow_state == ReportState.Start:
                # Future TODO: More sophisticated message processing
                if 'spam' in content:
                    self.flow_state = ReportState.Spam
                    return scam_options
                if 'fake account' in content:
                    self.flow_state = ReportState.Fake
                    return fake_account_options
                if 'harassment' in content or 'bully' in content:
                    # For logical understand in case we want to track what responses are entered.
                    self.flow_state = ReportState.Bully
                    self.flow_state = ReportState.Thanks
                    return final_options
                if 'post' in content or 'inappropriate' in content or 'things' in content:
                    self.flow_state = ReportState.Post
                    return post_options
                if 'scam' in content:
                    self.flow_state = ReportState.Scam
                    return scam_options
                if 'something' in content or 'else' in content:
                    self.flow_state = ReportState.Else
                    return scam_options
                
            if self.flow_state == ReportState.Spam:
                if 'fake account' in content:
                    self.flow_state = ReportState.Fake
                    return fake_account_options
                else:
                    self.flow_state = ReportState.Thanks
                    return final_options
            
            if self.flow_state == ReportState.Fake:
                self.flow_state = ReportState.Thanks
                return final_options
            
            if self.flow_state == ReportState.Bully:
                # Currently should not be possible to be in this state
                self.flow_state = ReportState.Thanks
                return final_options
            
            if self.flow_state == ReportState.Post:
                self.flow_state = ReportState.Thanks
                return final_options
            
            if self.flow_state == ReportState.Scam:
                self.flow_state = ReportState.Thanks
                return final_options
            
            if self.flow_state == ReportState.Else:
                self.flow_state = ReportState.Thanks
                return final_options
            
            if self.flow_state == ReportState.Thanks:
                self.state = State.REPORT_COMPLETE
                self.flow_state = ReportState.End
                if 'y' in content:
                    # Block the user
                    pass
                return

            return ["Unexpected state in reporting flow. Type `cancel` and start a new report."]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

