from enum import Enum, auto
import discord
import re

class ModState(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    
    HARASSMENT_CHOSEN = auto()
    HARASSMENT_TAKE_ACTION = auto()

    OFFENSIVE_CONTENT_CHOSEN = auto()
    OFFENSIVE_CONTENT_NOT_INCITING_VIOLENCE = auto()
    OFFENSIVE_CONTENT_INCITING_VIOLENCE = auto()
    OFFENSIVE_DANGEROUS_DEPICTION = auto()
    OFFENSIVE_TERRORISM = auto()
    OFFENSIVE_ANIMAL_ABUSE = auto()
    OFFENSIVE_VIOLENCE_OTHER = auto()

    URGENT_VIOLENCE_CHOSEN = auto()
    URGENT_SELF_HARM = auto()
    URGENT_DIRECT_THREAT = auto()

    OTHERS_CHOSEN = auto()
    OTHERS_REVIEW_TEAM = auto()

    BLOCK_USER = auto()

class ModReport:
    START_KEYWORD = "mod"

    def __init__(self, client, three_person_team_channel, user_flag_counts):
        self.state = ModState.REPORT_START
        self.client = client
        self.flagged_message = None
        self.mod_channel = None
        self.follow_up_message_id = None
        self.linked_message = None
        self.dm_channel = None
        self.three_person_team_channel = three_person_team_channel
        self.user_flag_counts = user_flag_counts
    
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

            # Here we've found the message - it's up to you to decide what to do next!
            # await message.channel.send(
            #     f"I found this message:\n"
            #     f"```{self.flagged_message.author.name}: {self.flagged_message.content}```\n"
            #     "Please review the message and take appropriate action."
            # )
            self.state = ModState.MESSAGE_IDENTIFIED

            await message.channel.send(
                f"I found this message and will now start the moderation process privately."
            )

            self.dm_channel = await message.author.create_dm()

            sent_message = await self.dm_channel.send(
                f"I found this message:\n"
                f"```{self.flagged_message.author.name}: {self.flagged_message.content}```\n"
                "Please react with the corresponding number for how to take the appropriate action with the flagged message:\n"
                "1️⃣ - Harassment\n"
                "2️⃣ - Offensive Content\n"
                "3️⃣ - Urgent Violence\n"
                "4️⃣ - Others/I don't like this\n"
                "5️⃣ - Cancel manual report")
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
            elif reaction == '5️⃣':
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        # OTHERS FLOW --------------------------------------------------------------
        elif self.state == ModState.OTHERS_CHOSEN:
            if reaction == '1️⃣':
                self.state = ModState.AWAITING_MESSAGE
                await self.handle_message(self.linked_message)
            elif reaction == '2️⃣':
                # send to review team
                await self.three_person_team_channel.send(
                    f"User flagged the following message as 'Other'. Now pending further moderation.\n"
                    f"```{self.flagged_message.content}```")

                await self.dm_channel.send("Report sent to three-person review team for further moderation. This moderation process is complete and further action will be pending.")
                self.state = ModState.OTHERS_REVIEW_TEAM
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        # HARASSMENT FLOW --------------------------------------------------------------

        elif self.state == ModState.HARASSMENT_CHOSEN:
            if reaction == '1️⃣':
                self.state = ModState.HARASSMENT_TAKE_ACTION
                await self.handle_harassment_take_action_reaction()
            elif reaction == '2️⃣':
                await self.dm_channel.send("No action taken. This moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.HARASSMENT_TAKE_ACTION:
            if reaction == '1️⃣':
                # remove post
                await self.dm_channel.send("Removing post...")
                await self.flagged_message.delete()
                await self.dm_channel.send("Removed post. This moderation process is complete.")
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
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return

        # OFFENSIVE CONTENT FLOW --------------------------------------------------------------   
        elif self.state == ModState.OFFENSIVE_CONTENT_CHOSEN:
            if reaction == '1️⃣':
                self.state = ModState.OFFENSIVE_CONTENT_NOT_INCITING_VIOLENCE
                await self.handle_offensive_content_not_inciting_violence_reaction()
            elif reaction == '2️⃣':
                self.state = ModState.OFFENSIVE_CONTENT_INCITING_VIOLENCE
                await self.handle_offensive_content_inciting_violence_reaction()
            elif reaction == '3️⃣':
                # cancel manual moderation
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_CONTENT_NOT_INCITING_VIOLENCE or self.state == ModState.OFFENSIVE_DANGEROUS_DEPICTION:
            if reaction == '1️⃣':
                # remove post
                await self.dm_channel.send("Removing post...")
                # remove post
                await self.flagged_message.delete()
                await self.dm_channel.send("This post has been removed and the moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '2️⃣':
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_CONTENT_INCITING_VIOLENCE:
            if reaction == '1️⃣':
                self.state = ModState.OFFENSIVE_DANGEROUS_DEPICTION
                await self.handle_dangerous_depiction_violence_reaction()
            elif reaction == '2️⃣':
                self.state = ModState.OFFENSIVE_TERRORISM
                await self.handle_offensive_terrorism_reaction()
            elif reaction == '3️⃣':
                self.state = ModState.OFFENSIVE_ANIMAL_ABUSE
                await self.handle_offensive_animal_abuse_reaction()
            elif reaction == '4️⃣':
                self.state = ModState.OFFENSIVE_VIOLENCE_OTHER
                await self.handle_offensive_violence_other_reaction()
            elif reaction == '5️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_TERRORISM:
            if reaction == '1️⃣':
                # ban user
                await self.flagged_message.channel.send(f"User {self.flagged_message.author.name} has been banned.")
                
                # removing post
                await self.flagged_message.delete()

                # notify law enforcement
                # basically do nothing... just a simulation
                await self.dm_channel.send("Removed post, banned user, and sent automatic report to law enforcement. The moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '2️⃣':
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_ANIMAL_ABUSE:
            if reaction == '1️⃣':
                # removing post
                await self.flagged_message.delete()
                # notify APS
                # basically do nothing... just a simulation
                await self.dm_channel.send("Removed post and sent automatic report to animal protective services. The moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '2️⃣':
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.OFFENSIVE_VIOLENCE_OTHER:
            if reaction == '1️⃣': # yes, fits with other inciting violence categories
                await self.handle_offensive_content_inciting_violence_reaction()
                self.state = ModState.OFFENSIVE_CONTENT_INCITING_VIOLENCE
            elif reaction == '2️⃣':
                # send to review team
                await self.three_person_team_channel.send(
                    f"User flagged the following message as 'Inciting Violence -> Other'. Now pending further moderation.\n"
                    f"```{self.flagged_message.content}```")

                await self.dm_channel.send("Report sent to three-person review team for further moderation. This moderation process is complete and further action will be pending.")
                self.state = ModState.OTHERS_REVIEW_TEAM
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return

        # URGENT VIOLENCE FLOW --------------------------------------------------------------

        elif self.state == ModState.URGENT_VIOLENCE_CHOSEN:
            if reaction == '1️⃣':
                self.state = ModState.URGENT_SELF_HARM
                await self.handle_urgent_self_harm_reaction()
            elif reaction == '2️⃣':
                self.state = ModState.URGENT_DIRECT_THREAT
                await self.handle_urgent_direct_threat_reaction()
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.URGENT_SELF_HARM:
            if reaction == '1️⃣':
                # send resources to user
                await self.flagged_message.author.send("We have seen your message and are here to help. Here are some mental health resources: [link]")
                # remove post
                await self.flagged_message.delete()
                await self.dm_channel.send("Removed post and sent mental health resources to user. The moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '2️⃣':
                # removing post
                await self.flagged_message.delete()
                await self.dm_channel.send("Removed post. The moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return
            
        elif self.state == ModState.URGENT_DIRECT_THREAT:
            if reaction == '1️⃣':
                # No action
                await self.dm_channel.send("No action taken. The moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '2️⃣':
                # ban user
                await self.flagged_message.channel.send(f"User {self.flagged_message.author.name} has been banned.")

                # removing post
                await self.flagged_message.delete()

                # notify law enforcement
                # basically do nothing... just a simulation
                await self.dm_channel.send("Removed post, banned user, and sent automatic report to law enforcement. The moderation process is complete.")
                self.state = ModState.REPORT_COMPLETE
            elif reaction == '3️⃣':
                # cancel
                await self.dm_channel.send("Canceled manual moderation.")
                self.state = ModState.REPORT_COMPLETE
            else:
                # Invalid reaction, ignore it
                return

        


    # OTHERS FLOW ----------------------------------------------------------
    async def handle_others_reaction(self):
        # ask if fits with other high level categories
        await self.send_follow_up_question(
                "Does this fit with the other categories (Harassment, Offensive Content, Urgent Violence)? React for yes or no.\n"
                "1️⃣ - Yes -> Choose appropriate category\n"
                "2️⃣ - No -> Forward to review team\n"
                "3️⃣ - Cancel")
        
    # HARASSMENT FLOW --------------------------------------------------------------

    async def handle_harassment_reaction(self):
        # Is the harrassment related to any of the following categories?
        await self.send_follow_up_question(
                "Does the harassment fit under trolling, impersonation, direct hate speech, doxing, or unwanted sexual content?\n"
                "1️⃣ - Yes -> May remove post, suspend, or ban user\n"
                "2️⃣ - No -> No action\n"
                "3️⃣ - Cancel")
        
    async def handle_harassment_take_action_reaction(self):
        # based on how many times the user has been flagged, choose an option
        flag_counts = 0
        if self.flagged_message.author.id in self.user_flag_counts:
            flag_counts = self.user_flag_counts[self.flagged_message.author.id]
        await self.send_follow_up_question(
                f"The user {self.flagged_message.author.name} has been previously flagged {flag_counts} times. Choose an option for action\n"
                "1️⃣ - Less than 5 times -> Remove post\n"
                "2️⃣ - Greater than 5 times -> Suspend user\n"
                "3️⃣ - Greater than 10 times -> Ban user\n"
                "4️⃣ - Cancel")

    # OFFENSIVE CONTENT FLOW --------------------------------------------------------------
    async def handle_offensive_content_reaction(self):
        # Ask follow-up questions specific to offensive content
        # await self.send_follow_up_question("Is this message inciting violence? (React with 1️⃣ for Yes, 2️⃣ for No)")
        await self.send_follow_up_question(
                "Please react with the corresponding number to deal with offensive content:\n"
                "1️⃣ - Sexually graphic content, CSAM, protected characteristics, or drug use -> Remove post\n"
                "2️⃣ - Inciting Violence -> Escalate to outside services, or remove post\n"
                "3️⃣ - Cancel\n")
        
    async def handle_offensive_content_not_inciting_violence_reaction(self):
        # Ask to remove post for offensive content that is not inciting violence
        await self.send_follow_up_question(
                "Please react with a corresponding number to confirm action:\n"
                "1️⃣ - Remove Post\n"
                "2️⃣ - Cancel")

    async def handle_offensive_content_inciting_violence_reaction(self):
        # Handle offensive content that is inciting violence
        await self.send_follow_up_question(
                "Please react with a corresponding number to further categorize inciting/glorifying violence:\n"
                "1️⃣ - Dangerous Acts, or Depiction of Physical Violence -> Remove post\n"
                "2️⃣ - Terrorism -> Escalate to law enforcement\n"
                "3️⃣ - Animal Abuse -> Escalate to animal protective services\n"
                "4️⃣ - Other\n"
                "5️⃣ - Cancel")
        
    async def handle_dangerous_depiction_violence_reaction(self):
        # Ask to remove post for offensive content that is a dangerous act or depiction of physical violence
        await self.send_follow_up_question(
                "Please react with a corresponding number to confirm action:\n"
                "1️⃣ - Remove Post\n"
                "2️⃣ - Cancel")
        
    async def handle_offensive_terrorism_reaction(self):
        # Ask to remove post, ban user, and notify law enforcement
        await self.send_follow_up_question(
                "Please react with a corresponding number to confirm action:\n"
                "1️⃣ - Remove post, ban user, and report case to law enforcement\n"
                "2️⃣ - Cancel")
        
    async def handle_offensive_animal_abuse_reaction(self):
        # ask to remove post and notify law enforcement
        await self.send_follow_up_question(
                "Please react with a corresponding number to confirm action:\n"
                "1️⃣ - Remove post and report case to animal protective services\n"
                "2️⃣ - Cancel")
        
    async def handle_offensive_violence_other_reaction(self):
        # ask if fits with other categories
        await self.send_follow_up_question(
                "Does this fit with the other categories of inciting violence? React for yes or no.\n"
                "1️⃣ - Yes -> Choose appropriate category\n"
                "2️⃣ - No -> Forward to review team\n"
                "3️⃣ - Cancel")
        
    # URGENT VIOLENCE FLOW --------------------------------------------------------------
    
    async def handle_urgent_violence_reaction(self):
        # Is the urgent violence related to self harm or a direct threat to another user?
        await self.send_follow_up_question(
                "Please react with a corresponding number to categorize the urgent violence.\n"
                "1️⃣ - Self Harm -> May remove post or send mental health resources\n"
                "2️⃣ - Direct Threat on Another User -> May escalate to ban, suspension, content removal, or law enforcement\n"
                "3️⃣ - Cancel")
    
    async def handle_urgent_self_harm_reaction(self):
        # Ask to remove post or send mental health resources if the enough veracity
        await self.send_follow_up_question(
                "Please determine the veracity of the post and react for one of the options:\n"
                "1️⃣ - Real issue -> Send mental health resources to user\n"
                "2️⃣ - No real issue -> Remove post\n"
                "3️⃣ - Cancel")
        
    async def handle_urgent_direct_threat_reaction(self):
        # Ask to remove post or send mental health resources if the enough veracity
        await self.send_follow_up_question(
                "Please determine the authenticity of the post and react for one of the options:\n"
                "1️⃣ - False Report -> No Action\n"
                "2️⃣ - Credible Threat -> Remove post, ban user, and report to law enforcement\n"
                "3️⃣ - Cancel")
        
    
    # Helper functions ----------------------------------------------------------
    
    async def send_follow_up_question(self, question):
        # Send a follow-up question and update the state
        # sent_message = await self.flagged_message.channel.send(question)
        sent_message = await self.dm_channel.send(question)
        self.follow_up_message_id = sent_message.id
        # self.state = ModState.FOLLOW_UP_QUESTION_AWAITING_ANSWER

    def report_complete(self):
        return self.state == ModState.REPORT_COMPLETE
    
    def report_in_review_team(self):
        return self.state == ModState.OTHERS_REVIEW_TEAM
