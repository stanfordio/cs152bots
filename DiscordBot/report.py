from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    IS_MISLEADING = auto()
    MISLEADING_RESPONSE_OBTAINED = auto()  
    LAST_USER_INPUT = auto() 

    MESSAGE_BLOCKED = auto()   
    LAST_USER_INPUT_MISLEADING = auto()

    MOD_START = auto()
    ADDITIONAL_ACTION = auto() 
    ADDITIONAL_ACTION_NOT_MISINFO = auto()
    POST_REMOVAL = auto()
    NOTIFY_OTHERS = auto()  
    REVIEW_OTHERS = auto()

    USER_BAN_DECISION = auto()  
    USER_BAN_DECISION_CONFIRM = auto()  
    NOTIFY_DECISION = auto()  
    REMOVAL_DECISION = auto()  
    NO_ACTION = auto()  
    


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, reporter_id, report_id):
        self.state = State.REPORT_START
        self.client = client
        self.reporter_id = reporter_id
        self.message = None
        self.user_context = None
        self.is_misleading = None
        self.is_misattributed = None
        self.is_untrue = None
        self.report_code = ''
        self.mod_review = False
        self.ismisinfo = False
        self.report_id = report_id

    
    
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
            # make self.message the offensive message
            self.message = message 
            self.guild = guild
            reply = "I found this message:" + "```" + message.author.name + ": " + message.content + "```"
            reply += "Please select the reason for reporting this message by entering the corresponding number. If you are in immediate danger, please contact your local emergency services in addition to reporting.\n"
            reply += "`1`: Spam\n"
            reply += "`2`: Harassment\n"
            reply += "`3`: Disturbing Content\n"
            reply += "`4`: Misleading Information"
            
            return [reply]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            # error catching 
            reply = "I'm sorry, but I don't recognize that input. Please enter a number from 1 to 4."
            # You will probably need to define extra states for the misleading information flow
            self.report_code += message.content
            if message.content == '1':
                reply = "Please select the type of spam by entering the corresponding number.\n"
                reply += "`1`: Phishing\n"
                reply += "`2`: Overwhelming amount of unwanted messages\n"
                reply += "`3`: Solicitation"
                self.state = State.LAST_USER_INPUT
            elif message.content == '2':
                reply = "Please provide more details about the harassment by entering the corresponding number.\n"
                reply += "`1`: Attacks based on my identity\n"
                reply += "`2`: Advocating for violence against me\n"
                reply += "`3`: Threatening to reveal my private information\n"
                reply += "`4`: Coordinated attacks against me by multiple individuals"
                self.state = State.LAST_USER_INPUT
            elif message.content == '3':
                reply = "Please select the kind of disturbing content by entering the corresponding number.\n"
                reply += "`1`: Child sexual exploitation\n"
                reply += "`2`: Content that depicts or advocates for self harm\n"
                reply += "`3`: Gore\n"
                reply += "`4`: Hate speech\n"
                reply += "`5`: Content that advocates for or glorifies violence"
                self.state = State.LAST_USER_INPUT
            elif message.content == '4':
                reply = "Is this information misleading (requires more context), misattributed (incorrect source or speaker), or untrue (deliberately false)?\n"
                reply += "`1`: Misleading (requires more context)\n"
                reply += "`2`: Misattributed (incorrect source or speaker)\n"
                reply += "`3`: Untrue (deliberately false)"
                self.state = State.IS_MISLEADING
                self.ismisinfo = True
            return [reply]
            
        if self.state == State.IS_MISLEADING:
            reply = "I'm sorry, but I don't recognize that input. Please enter a number from 1 to 3."
            self.report_code += message.content
            if message.content == '1':
                reply = "As concisely as possible, please provide any context you believe is missing. You may include links (news articles, original source) where appropriate."
                self.is_misleading = True
                self.state = State.MISLEADING_RESPONSE_OBTAINED
            elif message.content == '2':
                reply = "If you have access to the original quote or speaker, please provide it here."
                self.is_misattributed = True
                self.state = State.MISLEADING_RESPONSE_OBTAINED
            elif message.content == '3':
                reply = "Please copy-paste the portion of the text containing untruths. If it is the entire text, you may leave this blank."
                self.is_untrue = True
                self.state = State.MISLEADING_RESPONSE_OBTAINED
            return [reply]
        
        if self.state == State.MISLEADING_RESPONSE_OBTAINED:
            self.user_context = message.content
            self.report_code += '0'
            reply = "Is this post related at all to any recent protests, elections, or government policies?\n"
            reply += "`1`: Protests\n"
            reply += "`2`: Elections\n"
            reply += "`3`: Government policies\n"
            reply += "`4`: None of the above"
            self.state = State.LAST_USER_INPUT
            return [reply]

        
        
            # todo: misleading info flow

        if self.state == State.LAST_USER_INPUT:
            self.report_code += message.content 
            #here message is the user numerical input corresponding to the type of spam, harassment, disturbing content, or misleading info
            reply = "Thank you for reporting. Our content moderation team will review the message and decide on an appropriate course of action. This may include post removal, account suspension, or placement of the account in read-only mode.\n\n"
            reply += "In the meantime, we've hid the reported message from your view.\n"
            reply += "Would you like to mute or block the offending user?\n"
            reply += "`1`: Mute\n"
            reply += "`2`: Block\n"
            reply += "`3`: Neither"
            self.state = State.MESSAGE_BLOCKED
            return [reply]
        
        if self.state == State.MESSAGE_BLOCKED:
            reply = "I'm sorry, but I don't recognize that input. Please enter a number from 1 to 3."
            if message.content == '1':
                reply = "The user has been muted."
                self.state = State.MOD_START
                self.mod_review = True
            elif message.content == '2':
                reply = "The user has been blocked."
                self.state = State.MOD_START
                self.mod_review = True
            elif message.content == '3':
                reply = "The user has not been muted or blocked."
                self.state = State.MOD_START
                self.mod_review = True
            return [reply]
        
        return []

    async def mod_flow(self, message):  
        if self.state == State.MOD_START:
            if not self.ismisinfo:
                # reply = f"Report from user: {self.reporter_id}. Not in a category under our purview. This is the end of the process"
                # self.state = State.REPORT_COMPLETE
                reply =  "We have received the following moderation request:"
                reply += f"\nUser filing report: {self.reporter_id}"
                reply += f"\nMessage reported:"+ "```" + self.message.author.name + ": " + self.message.content + "```"
                reply += "\n\nIs further action necessary?"
                reply += f"\n REPORT_ID: {self.report_id}\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.ADDITIONAL_ACTION_NOT_MISINFO
                return [reply]

            misinfo_type_description = ""
            if(self.is_misattributed):
                misinfo_type_description = "Misattributed"
            if(self.is_misleading):
                misinfo_type_description = "Misleading"
            if(self.is_untrue):
                misinfo_type_description = "Untrue"

            reply =  "We have received the following moderation request:"
            reply += f"\nUser filing report: {self.reporter_id}"
            reply += f"\nMessage reported:"+ "```" + self.message.author.name + ": " + self.message.content + "```"
            reply += f"\nMessage category: " + misinfo_type_description
            reply += f"\nContext provided by reporter: " + self.user_context
            reply += f"\nWe have returned the following potentially related information from our automated fact-checker: \nExample Fact 1: The world is round. \nExample Fact 2: Joe Biden won the 2020 election. \nExample 3: The Cleveland Caveliers, a top tier team from a top tier city, have won more championships than the Denver Nuggets. "
            reply += "\n\nIs additional context or further action necesary?\n"
            reply += f"\n REPORT_ID: {self.report_id}\n"
            reply += f"`{self.report_id}:1`: Yes\n"
            reply += f"`{self.report_id}:2`: No\n"
            self.state = State.ADDITIONAL_ACTION
            return [reply]
        
        if self.state == State.ADDITIONAL_ACTION_NOT_MISINFO:
            await self.message.delete()
            reply = "Post removed. \n"
            self.state = State.REPORT_COMPLETE
              
        if self.state == State.ADDITIONAL_ACTION:
            reply = f"I'm sorry, but I don't recognize that input. Please enter {self.report_id}:1 or {self.report_id}:2"
            if message.content == f'{self.report_id}:1':
                reply = "We found the following other posts with similar language or from the same author: \n[Example 1] \n[Example 2]\n"
                reply += "Should this post be removed?\n"
                reply += f"\n REPORT_ID: {self.report_id}\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.REMOVAL_DECISION
                return [reply]
            elif message.content == f'{self.report_id}:2':
                reply = "No action taken. Please add a note explaining your decision to the reporter.\n"
                self.state = State.NO_ACTION
                return [reply]
            return [reply]
        
        if self.state == State.NO_ACTION:
            self.moderator_response = message.content
            reply = "Thank you. Review complete."
            self.state = State.REPORT_COMPLETE
            return [reply]

        if self.state == State.REMOVAL_DECISION:
            reply = f"I'm sorry, but I don't recognize that input. Please enter {self.report_id}:1 or {self.report_id}:2"
            if message.content == f'{self.report_id}:1':
                await self.message.delete()
                reply = "Post removed. \n"
                reply += "Should others who saw this post be notified?\n"
                reply += f"\n REPORT_ID: {self.report_id}\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.NOTIFY_DECISION
                return [reply]
            elif message.content == f'{self.report_id}:2':
                await self.message.reply("Potential cap alert! Here's some context")
                reply = "Context added. "
                reply += "Should others who saw this post be notified?\n"
                reply += f"\n REPORT_ID: {self.report_id}\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.NOTIFY_DECISION
                return [reply]
            return [reply]
        
        if self.state == State.NOTIFY_DECISION:
            reply = f"I'm sorry, but I don't recognize that input. Please enter {self.report_id}:1 or {self.report_id}:2"
            if message.content == f'{self.report_id}:1':
                reply = "Affected users notified. "
                reply += "Should this user, and associated users, be flagged for potential removal?\n"
                reply += f"\n REPORT_ID: {self.report_id}\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.USER_BAN_DECISION
                return [reply]
            elif message.content == f'{self.report_id}:2':
                reply = "Should this user, and associated users, be flagged for potential removal?\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.USER_BAN_DECISION
                return [reply]
            return [reply]
        

        if self.state == State.USER_BAN_DECISION:
            reply = f"I'm sorry, but I don't recognize that input. Please enter {self.report_id}:1 or {self.report_id}:2"
            if message.content == f'{self.report_id}:1':
                reply = "\nRequesting Confirmation. "
                reply += "\n [Confirmation from 2nd moderator] Should this user, and associated users, be flagged for potential removal?"
                reply += f"\n REPORT_ID: {self.report_id}\n"
                reply += f"`{self.report_id}:1`: Yes\n"
                reply += f"`{self.report_id}:2`: No\n"
                self.state = State.USER_BAN_DECISION_CONFIRM
                return [reply]
            elif message.content == f'{self.report_id}:2':
                reply = "User not flagged. Review Complete"
                self.state = State.REPORT_COMPLETE
                return [reply]
            return [reply]
        
        if self.state == State.USER_BAN_DECISION_CONFIRM:
            reply = f"I'm sorry, but I don't recognize that input. Please enter {self.report_id}:1 or {self.report_id}:2"
            if message.content == f'{self.report_id}:1':
                reply = "User flagged. Review Complete"
                self.state = State.REPORT_COMPLETE
                return [reply]
            elif message.content == f'{self.report_id}:2':
                reply = "User not flagged. Review Complete"
                self.state = State.REPORT_COMPLETE
                return [reply]
            return [reply]
            
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

