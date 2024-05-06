from enum import Enum, auto
import discord
import re

class ModState(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    HARASSMENT_CHOSEN = auto()

    OFFENSIVE_CONTENT_CHOSEN = auto()
    OFFENSIVE_CONTENT_NOT_INCITING_VIOLENCE = auto()
    OFFENSIVE_CONTENT_INCITING_VIOLENCE = auto()

    URGENT_VIOLENCE_CHOSEN = auto()
    OTHERS_CHOSEN = auto()
    BLOCK_USER = auto()

class ModReport:
    START_KEYWORD = "mod"

    def __init__(self, client):
        self.state = ModState.REPORT_START
        self.client = client
        self.flagged_message = None
        self.mod_channel = None
    
    async def handle_message(self, message):
        '''
        This function initiates the manual review process for flagged messages.
        '''

        if message.content == self.START_KEYWORD:
            await message.channel.send("Please paste the link to the message you want to review.")
            self.state = ModState.AWAITING_MESSAGE
            self.mod_channel = message.channel
            # print('awaiting message')
            return

        if self.state == ModState.AWAITING_MESSAGE:
            # print('awaiting message')
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                await message.channel.send("I'm sorry, I couldn't read that link. Please try again.")
                return
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                await message.channel.send("I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again.")
                return
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                await message.channel.send("It seems this channel was deleted or never existed. Please try again.")
                return
            try:
                self.flagged_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                await message.channel.send("It seems this message was deleted or never existed. Please try again.")
                return

            # Here we've found the message - it's up to you to decide what to do next!
            # await message.channel.send(
            #     f"I found this message:\n"
            #     f"```{self.flagged_message.author.name}: {self.flagged_message.content}```\n"
            #     "Please review the message and take appropriate action."
            # )
            self.state = ModState.MESSAGE_IDENTIFIED
            sent_message = await message.channel.send(
                f"I found this message:\n"
                f"```{self.flagged_message.author.name}: {self.flagged_message.content}```\n"
                "Please react with the corresponding number for how to take the appropriate action with the flagged message:\n"
                "1️⃣ - Harassment\n"
                "2️⃣ - Offensive Content\n"
                "3️⃣ - Urgent Violence\n"
                "4️⃣ - Others/I don't like this")
            self.abuse_category_message_id = sent_message.id
            return
    
    async def handle_reaction(self, payload, message):
        if self.state == ModState.MESSAGE_IDENTIFIED:
            if payload.message_id != self.abuse_category_message_id:
                # If the reaction is not on the abuse category message, ignore it
                await self.mod_channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            reaction = str(payload.emoji)

            if reaction == '1️⃣':
                self.state = ModState.HARASSMENT_CHOSEN
                await self.handle_harassment_reaction()
            elif reaction == '2️⃣':
                self.state = ModState.OFFENSIVE_CONTENT_CHOSEN
                await self.handle_offensive_content_reaction()
            elif reaction == '3️⃣':
                self.state = ModState.URGENT_VIOLENCE_CHOSEN
                await self.handle_urgent_violence_reaction()
            elif reaction == '4️⃣':
                self.state = ModState.OTHERS_CHOSEN
                await self.handle_others_reaction()
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_CONTENT_CHOSEN:
            if payload.message_id != self.follow_up_message_id:
                # If the reaction is not on the follow-up message, ignore it
                await self.mod_channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            reaction = str(payload.emoji)

            if reaction == '1️⃣':
                self.state = ModState.OFFENSIVE_CONTENT_NOT_INCITING_VIOLENCE
                # await self.send_follow_up_question("Please review the message and take appropriate action.")
                await self.handle_offensive_content_not_inciting_violence_reaction()
            elif reaction == '2️⃣':
                self.state = ModState.OFFENSIVE_CONTENT_INCITING_VIOLENCE
                await self.handle_offensive_content_inciting_violence_reaction()
                
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_CONTENT_NOT_INCITING_VIOLENCE:
            if payload.message_id != self.follow_up_message_id:
                # If the reaction is not on the follow-up message, ignore it
                await self.mod_channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            reaction = str(payload.emoji)

            if reaction == '1️⃣':
                # remove post
                await self.mod_channel.send("Removing post...")
                # remove post
                await self.flagged_message.delete()
                await self.mod_channel.send("This post has been removed and the moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
                
            elif reaction == '2️⃣':
                await self.mod_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
                
            else:
                # Invalid reaction, ignore it
                return

    async def handle_harassment_reaction(self):
        # Ask follow-up questions specific to harassment
        pass
        # await self.send_follow_up_question("Is the message sexually graphic content, CSAM, relates to protected characteristics, or drug use? (React with 1️⃣ for Yes, 2️⃣ for No)")
    
    async def handle_offensive_content_reaction(self):
        # Ask follow-up questions specific to offensive content
        # await self.send_follow_up_question("Is this message inciting violence? (React with 1️⃣ for Yes, 2️⃣ for No)")
        await self.send_follow_up_question(
                "Please react with the corresponding number to deal with offensive content:\n"
                "1️⃣ - Sexually graphic content, CSAM, protected characteristics, or drug use -> remove post\n"
                "2️⃣ - Inciting Violence -> continue, escalate to outside services, or remove post")
        
    async def handle_offensive_content_not_inciting_violence_reaction(self):
        # Ask to remove post for offensive content that is not inciting violence
        await self.send_follow_up_question(
                "Please react with a corresponding number to confirm action:\n"
                "1️⃣ - Remove Post\n"
                "2️⃣ - Cancel ")

    async def handle_offensive_content_inciting_violence_reaction(self):
        # Handle offensive content that is inciting violence
        pass
    
    async def handle_urgent_violence_reaction(self):
        # Handle urgent violence reaction (if needed)
        # This could involve taking immediate action or escalating the issue
        pass
    
    async def handle_others_reaction(self):
        # Handle "Others" reaction (if needed)
        # This could involve asking for more details or other follow-up actions
        pass
    
    async def send_follow_up_question(self, question):
        # Send a follow-up question and update the state
        # sent_message = await self.flagged_message.channel.send(question)
        sent_message = await self.mod_channel.send(question)
        self.follow_up_message_id = sent_message.id
        # self.state = ModState.FOLLOW_UP_QUESTION_AWAITING_ANSWER

    def report_complete(self):
        return self.state == ModState.REPORT_COMPLETE
