from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()

    CATEGORY_IDENTIFIED = auto() #disinformation, nudity, etc
    TYPE_IDENTIFIED = auto() #political disinfo, health disinfo
    SUBTYPE_IDENTIFIED = auto() #vaccines, cures and treatments
    HARM_IDENTIFIED = auto()
    BLOCK_STEP = auto()

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
            return ["I found this message:```" + message.author.name + ": " + message.content + "```\n",
                    message.author.name,
                    message.content]

        # TODO fill out the rest of the user reporting flow
        # seems like readme wants us to use this: https://discordpy.readthedocs.io/en/latest/api.html?highlight=on_reaction_add#discord.on_raw_reaction_add
        if self.state == State.MESSAGE_IDENTIFIED:           
            # get value based on reacts
            self.state = State.CATEGORY_IDENTIFIED
            return ["[PLACEHOLDER] What category does this content fall under?\n1 = disinformation\n2 = other reporting flow"]

        #etc etc 
        # return based on expected format outlined in bot.py, 
        # where 0th element is the appropriate messaage and the rest are data

        if self.state == State.BLOCK_STEP:
            # if user wants to block then block
            user_wants_to_block = True
            return [user_wants_to_block]

        return []
    
    
    def report_start(self):
        return self.state == State.REPORT_START
    def awaiting_message(self):
        return self.state == State.AWAITING_MESSAGE
    def message_identified(self):           
        return self.state == State.MESSAGE_IDENTIFIED
    def category_identified(self):
        return self.state == State.CATEGORY_IDENTIFIED
    def type_identified(self):
        return self.state == State.TYPE_IDENTIFIED
    def subtype_identified(self):
        return self.state == State.SUBTYPE_IDENTIFIED
    def harm_identified(self):
        return self.state == State.HARM_IDENTIFIED
    def block_step(self):
        return self.state == State.BLOCK_STEP
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

