from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    
    AWAIT_CONTENT_TYPE = auto()
    AWAIT_SPAM_TYPE = auto()
    
    # ADD MORE STATES HERE FOR DIFFERENT FLOW STUFF

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        
        # 1 is Imminent Danger, 2 is Spam, 3 is Nudity or Graphic, 4 is Disinformation, 5 is Hate speech/harrassment, 6 is Other
        self.abuse_type = None
        
    
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
            self.state = State.AWAIT_CONTENT_TYPE
            # return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #         "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
            # return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #         "if you want to report, please specify the type of AI-generated content you see."] \
            return   [' You can select from 1. Imminent Danger, 2. Spam, 3. Nudity or Graphic, 4. Disinformation, 5. Hate speech/harrassment, 6. Other (including satire, memes, commentary, couterspeech, etc.)'] \
                            + ['Please type the number of the content type you see.']

            
        if self.state == State.AWAIT_CONTENT_TYPE:
            self.state = State.AWAIT_SPAM_TYPE
            try:
                selection = int(message.content)
                self.abuse_type = selection
            except:
                return ["Please type the number of the content type you see."]
            
            return [f'abuse type {selection} reported. Thank you for your report.']

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

