from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    BLOCK_START = auto()
    AWAITING_BLOCK = auto()
    AWAITING_BLOCK_CONFIRM = auto()
    BLOCK_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    BLOCK_KEYWORD = "block"

    def __init__(self, client):
        self.state = None  # Allows transition between `report` and `block` midway through processes
        self.client = client
        self.message = None
        self.reported_user = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Process cancelled."]

        if message.content.startswith(self.BLOCK_KEYWORD):
            return await self.handle_block(message)
        
        if message.content.startswith(self.START_KEYWORD):
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
            return ["<insert rest of reporting flow here>"]

        return []


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


    async def handle_block(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.BLOCK_COMPLETE

        if message.content.startswith(self.START_KEYWORD):
            return await self.handle_message(message)
        
        if message.content.startswith(self.BLOCK_KEYWORD):
            self.state = State.BLOCK_START
            reply = "Thank you for starting the blocking process.\n"
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the username of the user you want to block.\n"
            reply += "You can obtain this by right-clicking the user, clicking `Profile,` and copying the username."
            self.state = State.AWAITING_BLOCK
            return [reply]

        if self.state == State.AWAITING_BLOCK:
            self.reported_user = message.content.lower()
            reply = "Please confirm that you would like to block '" + self.reported_user + "'\n"
            reply += "You will no longer be able to interact with them.\n"
            reply += "Please reply with `yes` or `no`."
            self.state = State.AWAITING_BLOCK_CONFIRM
            return [reply]
        
        if self.state == State.AWAITING_BLOCK_CONFIRM:
            if message.content.lower() == "yes":
                reply = "Thank you. User '" + self.reported_user + "' has been blocked."
            else:
                reply = "Thank you. User '" + self.reported_user + "' has not been blocked."
            return [reply]

        return []


    def block_complete(self):
        return self.state == State.BLOCK_COMPLETE