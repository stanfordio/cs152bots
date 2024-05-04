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
        self.abuse_category_message_id = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            await message.channel.send("Report cancelled.")
            return
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            await message.channel.send(reply)
            return
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                await message.channel.send("I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel.")
                return
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                await message.channel.send("I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again.")
                return
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                await message.channel.send("It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel.")
                return
            try:
                identified_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                await message.channel.send("It seems this message was deleted or never existed. Please try again or say `cancel` to cancel.")
                return

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            sent_message = await message.channel.send(
                f"I found this message:\n"
                f"```{identified_message.author.name}: {identified_message.content}```\n"
                "Please react with the corresponding number for the reason of your report:\n"
                "1️⃣ - Harassment\n"
                "2️⃣ - Offensive Content\n"
                "3️⃣ - Urgent Violence\n"
                "4️⃣ - Others/I don't like this")
            self.abuse_category_message_id = sent_message.id
            return
        
        return
    
    async def handle_reaction(self, payload, message):
        if self.state == State.MESSAGE_IDENTIFIED and payload.message_id == self.abuse_category_message_id:
            if str(payload.emoji) == '1️⃣':
                await message.channel.send("You've reported harassment")
                return
            elif str(payload.emoji) == '2️⃣':
                await message.channel.send("You've reported offensive content")
                return
            elif str(payload.emoji) == '3️⃣':
                await message.channel.send("You've reported urgent violence")
                return
            elif str(payload.emoji) == '4️⃣':
                await message.channel.send("You've reported others/I don't like this")
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, or 4️⃣")
        
        return


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

