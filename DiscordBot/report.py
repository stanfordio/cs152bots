from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    POSTING_IDENTITY_IDENTIFIED = auto()
    CONTENT_TYPE_IDENTIFIED = auto()
    EXPECT_TARGET_SUBJECT = auto()
    EXPECT_VIOLENCEORNO = auto()
    DISMISINFO = auto()
    SWAY_OPINIONS = auto()
    READY_TO_SUBMIT = auto()
    SUBMIT_OR_NO = auto()
    REPORT_COMPLETE = auto()
    REPORT_THANKYOU = auto()
    REPORT_MOREORNOT = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    INCORRECT_RESPONSE = "Please ensure the response is in the correct format."

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = {}
        # self.message has fields: message, author, reason, posting_entity, content_type
    
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
            self.message['message'] = message.content
            self.message['author'] = message.author.name
            self.state = State.MESSAGE_IDENTIFIED
            return ["Please select a reason for reporting this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "1. Misleading/false information from government group\n2. Spam\n3. Nudity\n4. Bullying\n5. Fraud/Scam\n" + 
                    "Please respond with one of 1, 2, 3, 4, or 5."]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            # parsing for message category.
            if int(message.content) == 1:
                self.message['reason'] = "Misleading/false information from government group" 
                self.state = State.POSTING_IDENTITY_IDENTIFIED
                return ["Please select the affiliation of the posting entity.\n1. Government Official\n2. Government Agency\n3. Government State-Controlled Media\n" +
                        "4. Ex-Government Official\n5. Not Government Entity."]
            if int(message.content) == 2:
                self.message['reason'] = "Spam"
            if int(message.content) == 3:
                self.message['reason'] = "Nudity"
            if int(message.content) == 4:
                self.message['reason'] = "Bullying"
            if int(message.content) == 5:
                self.message['reason'] = "Fraud/Scam"
            if int(message.content) in [2, 3, 4, 5]:
                self.state == State.REPORT_THANKYOU
                return
            else: 
                return [self.INCORRECT_RESPONSE]
        
        if self.state == State.POSTING_IDENTITY_IDENTIFIED:
            if (int(message.content) == 1):
                self.message['posting_entity'] = "Government Official"
            if (int(message.content) == 2): 
                self.message['posting_entity'] = "Government Agency"
            if (int(message.content) == 3): 
                self.message['posting_entity'] = "Government State-Controlled Media"
            if (int(message.content) == 4): 
                self.message['posting_entity'] = "Ex-Government Official"
            if (int(message.content) == 5):
                self.state = State.MESSAGE_IDENTIFIED
                return ["Please select a different reporting reason."]
            if (int(message.content) in [1, 2, 3, 4]):
                return ["Please select one type of content that the reported message falls under.\n1. I just don\'t like it\n2. Dis/Misinformation\n" + 
                    "3. Inciting Harassment\n4. Hate Speech\n5. Swaying others opinion\n Please respond with one of 1, 2, 3, 4, or 5."]
            else:
                return [self.INCORRECT_RESPONSE]

        if self.state == State.CONTENT_TYPE_IDENTIFIED:
            # I just don't like it
            if (int(message.content) == 1): 
                # don't submit i just don't like it reports to moderator team
                self.state = State.REPORT_COMPLETE
                return ["Thanks for letting us know. We have blocked this users post from your feed. If the user\’s content makes you uncomfortable, you can use the block feature to no longer see their content"]
            # Dis/Misinformation
            elif (int(message.content) == 2): 
                self.message['content_type'] = "Dis/Misinformation"
                self.state = State.DISMISINFO
                return ["Please select one of the following categories of the dis/misinformation.\n1. Marginalized Groups\n2. Factually Incorrect\n Please respond with one of 1 or 2."]
            if (int(message.content) == 3): 
                self.message['content_type'] = "Inciting Harassment"
            if (int(message.content) == 4): 
                self.message['content_type'] = "Hate Speech"
            if (int(message.content) in [3, 4]):
                self.state = State.EXPECT_TARGET_SUBJECT 
                return ["Who\'s being targeted? Please limit your answer to 10 words."]
            if (int(message.content) == 5):
                self.state = State.SWAY_OPINIONS
                return ["What were the methods used to sway others\' beliefs? Respond with 1 for Dis/Misinformation. If not Dis/Misinformation, please type your answer in 20 words or less."]

        if self.state == State.SWAY_OPINIONS:
            if (int(message.content) == 1):
                self.state = State.DISMISINFO
                return
            else: 
                self.message['content_type'] = "Swaying others opinion"
                self.message['methods'] = message.content
                self.state = State.READY_TO_SUBMIT
                return
                
        if self.state == State.READY_TO_SUBMIT:
            self.state = State.SUBMIT_OR_NO
            return ["Are you ready to submit the report.\n1. Yes\n2. No, I would like to cancel the report.\nPlease select 1 or 2."]

        if self.state == State.SUBMIT_OR_NO:
            if (int(message.content) == 1):
                # INSERT CODE TO SEND TO MODERATOR CHANNEL
                self.state = State.REPORT_THANKYOU
                return
            elif (int(message.content) == 2):
                self.state = State.REPORT_COMPLETE
            else: 
                self.incorrect_response_format()

        if self.state == State.EXPECT_TARGET_SUBJECT: 
            target_subject = message.content
            self.state = State.EXPECT_VIOLENCEORNO
            return ["Does the reported message encourage violence?\n1. Yes\n2. No\n Please respond with 1 or 2."]
        
        if self.state == State.EXPECT_VIOLENCEORNO:
            if (int(message.content) == 1):
                self.message['violence'] = "Yes"
            if (int(message.content) == 2): 
                self.message['violence'] = "No"
            if (int(message.content) in [1, 2]):
                self.state = State.SUBMIT_OR_NO
                return
            else:
                return [self.INCORRECT_RESPONSE]
            

        if self.state == State.REPORT_THANKYOU:
            self.state = State.REPORT_MOREORNOT
            return["Thank you for submitting this report. We will review the reported content and determine whether the post will be flagged, removed, or kept up. If the user\’s content makes you uncomfortable, you can use the block feature to no longer see their content.\n" 
                   + "Are there additional posts you would like to report?\n1. Yes\n2. No\n Please with respond with one of 1 or 2."]
        
        if self.state == State.REPORT_MOREORNOT:
            if int(message.content) == 1:
                self.state = State.REPORT_START
                return
            elif int(message.content) == 2:
                self.state = State.REPORT_COMPLETE
                return["The reporting process is complete."]

        return []

    def incorrect_response_format(self):
        return ["Please ensure the response is in the correct format."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

