from enum import Enum, auto
import discord
import re

class ModState(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()


class ThreePersonReport:
    START_KEYWORD = "mod"

    def __init__(self, client, three_person_team_channel):
        self.state = ModState.REPORT_START
        self.client = client
        self.flagged_message = None
        self.mod_channel = None
        self.follow_up_message_id = None
        self.linked_message = None
        self.dm_channel = None
        self.three_person_team_channel = three_person_team_channel
    
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
            self.linked_message = message
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

            self.state = ModState.MESSAGE_IDENTIFIED

            await message.channel.send(
                f"I found this message and will now start the moderation process privately."
            )

            self.dm_channel = await message.author.create_dm()

            sent_message = await self.dm_channel.send(
                f"I found this message:\n"
                f"```{self.flagged_message.author.name}: {self.flagged_message.content}```\n"
                "Please approve this report. If approved, react with the corresponding number to take the appropriate action with the flagged message. Otherwise, send report to Trust and Safety Committee:\n"
                "1️⃣ - Remove Post\n"
                "2️⃣ - Suspend User (3 days) and Remove Post\n"
                "3️⃣ - Ban User, Remove Post\n"
                "4️⃣ - Contact Local Authorities, Ban User, Remove Post\n"
                "5️⃣ - Contact Animal Protection Services, Remove Post\n"
                "6️⃣ - Report to Trust and Safety Committee\n"
                "7️⃣ - Cancel")
            self.abuse_category_message_id = sent_message.id
            self.follow_up_message_id = sent_message.id
            return
    
    async def handle_reaction(self, payload, message):
        if payload.message_id != self.follow_up_message_id:
            # If the reaction is not on the follow-up message, ignore it
            await self.dm_channel.send("Please react to the message that contains emoji options to choose from.")
            return
            
        reaction = str(payload.emoji)
        if self.state == ModState.MESSAGE_IDENTIFIED:
            if reaction == '1️⃣':
                # remove post
                await self.dm_channel.send("Removing post.")
                await self.flagged_message.delete()
                await self.dm_channel.send("Post has been removed. This moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '2️⃣':
                user = self.flagged_message.author.name
                # suspend user
                await self.flagged_message.channel.send(f"User {user} has been suspended for 3 days.")
                # remove post
                await self.dm_channel.send("Removing post...")
                await self.flagged_message.delete()

                await self.dm_channel.send(f"Suspended user {user} for 3 days and removed post. This moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '3️⃣':
                user = self.flagged_message.author.name
                # ban user
                await self.flagged_message.channel.send(f"User {user} has been banned.")
                # remove post
                await self.dm_channel.send("Removing post...")
                await self.flagged_message.delete()

                await self.dm_channel.send(f"Banned user {user} and removed post. This moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '4️⃣':
                user = self.flagged_message.author.name
                # ban user
                await self.flagged_message.channel.send(f"User {user} has been banned.")
                # remove post
                await self.dm_channel.send("Removing post...")
                await self.flagged_message.delete()

                # contact authorities
                # do nothing for now

                await self.dm_channel.send(f"Sent automatic report to law enforcement, banned user {user}, and removed post. This moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '5️⃣':
                user = self.flagged_message.author.name
                
                # remove post
                await self.dm_channel.send("Removing post...")
                await self.flagged_message.delete()

                # contact APS
                # do nothing for now

                await self.dm_channel.send(f"Sent automatic report animal protection services and removed post. This moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '6️⃣':
                # send report to Trust and Safety Committee
                # do nothing for now

                await self.dm_channel.send("Sent report to Trust and Safety Committee. This moderation process will be pending further approval.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '7️⃣':
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
        
    
    # Helper functions ----------------------------------------------------------
    
    async def send_follow_up_question(self, question):
        # Send a follow-up question and update the state
        # sent_message = await self.flagged_message.channel.send(question)
        sent_message = await self.dm_channel.send(question)
        self.follow_up_message_id = sent_message.id
        # self.state = ModState.FOLLOW_UP_QUESTION_AWAITING_ANSWER

    def report_complete(self):
        return self.state == ModState.REPORT_COMPLETE

