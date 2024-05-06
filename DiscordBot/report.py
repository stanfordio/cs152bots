from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    HARASSMENT_CHOSEN = auto()
    OFFENSIVE_CONTENT_CHOSEN = auto()
    URGENT_VIOLENCE_CHOSEN = auto()
    OTHERS_CHOSEN = auto()
    BLOCK_USER = auto()
    INCITING_VIOLENCE_CHOSEN = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuse_category_message_id = None
        self.block_user_message_id = None
        self.harassment_type_message_id = None
        self.offensive_content_type_message_id = None
        self.inciting_violence_message_id = None
    
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
        
        if self.state == State.OTHERS_CHOSEN:
            # TODO: Save this message somehow

            self.state = State.BLOCK_USER
            sent_message = await message.channel.send(
                "Thank you for your report. Would you like to block this user?\n"
                "If so, please react to this message with 👍.\n"
                "Otherwise, react to this message with 👎."
            )
            self.block_user_message_id = sent_message.id
            return
        
        return
    
    async def handle_reaction(self, payload, message):
        if self.state == State.MESSAGE_IDENTIFIED:
            if payload.message_id != self.abuse_category_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣':
                self.state = State.HARASSMENT_CHOSEN
                sent_message = await message.channel.send(
                    "Please react with the corresponding number for which type of harassment you're reporting:\n"
                    "1️⃣ - Trolling\n"
                    "2️⃣ - Impersonation\n"
                    "3️⃣ - Directed Hate Speech\n"
                    "4️⃣ - Doxing\n"
                    "5️⃣ - Unwanted Sexual Content\n")
                self.harassment_type_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣':
                self.state = State.OFFENSIVE_CONTENT_CHOSEN
                sent_message = await message.channel.send(
                    "Please react with the corresponding number for which type of offensive content you're reporting:\n"
                    "1️⃣ - Protected Characteristics (race, color, religion etc.)\n"
                    "2️⃣ - Sexually Graphic Content\n"
                    "3️⃣ - Child Sexual Abuse Material\n"
                    "4️⃣ - Drug Use\n"
                    "5️⃣ - Inciting/Glorifying  Violence\n")
                self.offensive_content_type_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣':
                self.state = State.URGENT_VIOLENCE_CHOSEN
                await message.channel.send("You've reported urgent violence")
                return
            elif str(payload.emoji) == '4️⃣':
                self.state = State.OTHERS_CHOSEN
                await message.channel.send("We're here to help. Can you describe the issue in more detail?")
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, or 4️⃣")
            return
        
        if self.state == State.HARASSMENT_CHOSEN:
            if payload.message_id != self.harassment_type_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣':
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣':
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣':
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣':
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '5️⃣':
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, 4️⃣ or 5️⃣")
            return
        
        if self.state == State.OFFENSIVE_CONTENT_CHOSEN:
            if payload.message_id != self.offensive_content_type_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣': # Protected Characteristics
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣': # Sexually Graphic Content
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣': # Child Sexual Abuse Material
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣': # Drug Use
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '5️⃣': # Inciting/Glorifying Violence
                self.state = State.INCITING_VIOLENCE_CHOSEN
                sent_message = await message.channel.send(
                    "Please react with the corresponding number for which type of violence you're reporting:\n"
                    "1️⃣ - Dangerous Acts\n"
                    "2️⃣ - Terrorism\n"
                    "3️⃣ - Animal Abuse\n"
                    "4️⃣ - Depiction of Physical Violence\n"
                    "5️⃣ - Other\n"
                )
                self.inciting_violence_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, 4️⃣ or 5️⃣")
            return
        
        if self.state == State.INCITING_VIOLENCE_CHOSEN:
            if payload.message_id != self.inciting_violence_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣': # Dangerous Acts
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣': # Terrorism
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣': # Animal Abuse
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣': # Depiction of Physical Violence
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '5️⃣': # Other
                self.state = State.BLOCK_USER
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, 4️⃣ or 5️⃣")
            return

        if self.state == State.BLOCK_USER:
            if payload.message_id != self.block_user_message_id:
                await message.channel.send("Please respond by reacting directly to the block confirmation message above with the appropriate emoji.")
                return
            
            if str(payload.emoji) == '👍':
                self.state = State.REPORT_COMPLETE
                await message.channel.send("You have chosen to block the user, and we have processed your request. We appreciate your help in maintaining a safe community environment.")
                return
            elif str(payload.emoji) == '👎':
                self.state = State.REPORT_COMPLETE
                await message.channel.send("You have chosen not to block the user. We appreciate your help in maintaining a safe community environment.")
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 👍 or 👎")
            return
        
        return


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

