from enum import Enum, auto
import discord
import re

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
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
        
        if self.state == State.MESSAGE_IDENTIFIED:
<<<<<<< Updated upstream
            return ["<insert rest of reporting flow here>"]
=======
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

>>>>>>> Stashed changes

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

