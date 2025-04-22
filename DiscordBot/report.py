from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    PSEUDO_BAN_USER = auto()
    REMOVE_MESSAGE = auto()
    ADDING_INFO = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    ADD_KEYWORD = "add info"
    BAN_KEYWORD = "ban"
    REMOVE_KEYWORD = "remove"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.target_message = None
    
    async def remove_message(self):
        try:
            await self.target_message.delete()
            self.state = State.REPORT_COMPLETE
            return ["```" + self.target_message.author.name + ": " + self.target_message.content + "```" + " is now removed"]
        except discord.Forbidden:
            return ["❌ I lack permissions to delete that message."]

    def pseudo_ban_user(self):
        return [f"User: {self.target_message.author.name} banned for message {self.target_message.content}."]

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report completed."]
        
        elif self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        elif self.state == State.AWAITING_MESSAGE:
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
                self.target_message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```",
                    f""""{self.ADD_KEYWORD}" to add additional information,"""
                    f""""{self.BAN_KEYWORD}" to ban the user,"""
                    f""""{self.REMOVE_KEYWORD}" to remove the message."""]
        if self.target_message is not None:
            if message.content == self.ADD_KEYWORD:
                self.state = State.ADDING_INFO
            elif message.content == self.BAN_KEYWORD:
                return [f"User: {self.target_message.author.name} banned for message {self.target_message.content}."]
            elif message.content == self.REMOVE_KEYWORD:
                try:
                    await self.target_message.delete()
                    self.state = State.REPORT_COMPLETE
                    return ["```" + self.target_message.author.name + ": " + self.target_message.content + "```" + " is now removed"]
                except discord.Forbidden:
                    return ["❌ I lack permissions to delete that message."]
            #return ["<insert rest of reporting flow here>"]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

