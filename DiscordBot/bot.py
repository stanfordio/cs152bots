# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, State
import pdb
import heapq

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class Moderator:
    HELP_KEYWORD = "help"
    PEEK_KEYWORD = "peek"
    REVIEW_KEYWORD = "review"
    COUNT_KEYWORD = "count"
    SEVERITY_LEVELS = 4

class ModBot(discord.Client):

    NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # required to perceive user reactions in DMs for some weird reason. i spent so long on this. RIP.
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.filed_reports = {} # Map from user IDs to the state of their filed report
        self.reports_to_review = [] # Priority queue of (user IDs, index)  state of their filed report
        self.report_counter = 0 # Count of filed reports

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_reaction_add(self, reaction, user):
        '''
        This function is called whenever a reaction is added in a channel that the bot can see.
        '''
        # Ignore reactions from the bot
        if user.id == self.user.id:
            return

        print(f"User id: {user.id}")

        if user.id not in self.reports or reaction.message.guild: # Probably a moderator in this case?
            return

        report = self.reports[user.id]
        if reaction.message == report.message:
            #print("reaction detected!")
            await self.reports[user.id].handle_reaction(reaction)
            
            # "fake" a message from the user (this is a hack to use handle_dm)
            # (trust me.  this is so hacky and stupid but it works!!!. im smart #womeinSTEM)
            # <3
            bot_id = self.user.id
            fake_message = reaction.message
            fake_message.author.id = user.id

            await self.handle_dm(fake_message)
            self.user.id = bot_id
        

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            bot_message = await message.channel.send(r)
        
        self.reports[author_id].message = bot_message

        # handle reactions
        if self.reports[author_id].reaction_mode:
            
            if (self.reports[author_id].state == State.AWAITING_REASON):
                for _ in range(len(self.reports[author_id].REASONS)):
                    await bot_message.add_reaction(self.NUMBERS[_])
            elif (self.reports[author_id].state == State.AWAITING_SUBREASON):
                for _ in range(len(self.reports[author_id].SUB_REASONS[self.reports[author_id].reason])):
                    await bot_message.add_reaction(self.NUMBERS[_])
            elif (self.reports[author_id].state == State.ADDING_CONTEXT or 
                    self.reports[author_id].state == State.CHOOSE_BLOCK):
                await bot_message.add_reaction("✅")
                await bot_message.add_reaction("❌")
            elif (self.reports[author_id].state == State.AWAITING_REVIEW):
                for _ in range(Moderator.SEVERITY_LEVELS):
                    await bot_message.add_reaction(self.NUMBERS[_])
            print(self.reports[author_id].state)

        # If the report is filed, save it, cache it in a priority queue, and alert #mod channel for review.
        if self.reports[author_id].report_filed():
            if author_id in self.filed_reports:
                self.filed_reports[author_id].append(self.reports[author_id])
            else:
                self.filed_reports[author_id] = [self.reports[author_id]]
            
            # Add to priority queue
            priority = self.reports[author_id].priority()
            index = len(self.filed_reports[author_id]) - 1
            heapq.heappush(self.reports_to_review, (priority, self.report_counter, (author_id, index)))
            self.report_counter += 1

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" or "group-#-mod" channel
        if message.channel.name == f'group-{self.group_num}':
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))
            return 

        # Moderator flow
        if message.channel.name == f'group-{self.group_num}-mod':
            if message.content == Moderator.HELP_KEYWORD:
                reply =  "Use the `peek` command to look at the most urgent report.\n"
                reply += "Use the `count` command to see how many reports are in the review queue.\n"
                await message.channel.send(reply)
                return

            if message.content == Moderator.COUNT_KEYWORD:
                reply = f"There are currently {len(self.reports_to_review)} reports to review.\n"
                await message.channel.send(reply)
                return

            if message.content == Moderator.PEEK_KEYWORD:
                if len(self.reports_to_review) == 0:
                    reply = "No reports to review!"
                else:
                    reply = f"1 of {len(self.reports_to_review)} reports:\n"
                    _, _, info = self.reports_to_review[0]
                    author_id, index = info
                    report = self.filed_reports[author_id][index]
                    reply += report.summary()
                await message.channel.send(reply)
                return

            if message.content == Moderator.REVIEW_KEYWORD:
                if len(self.reports_to_review) == 0:
                    reply = "No reports to review!"
                    await message.channel.send(reply)
                    return

                # Review top item
                reply = f"1 of {len(self.reports_to_review)} reports:\n"
                _, _, info = self.reports_to_review[0]
                author_id, index = info
                report = self.filed_reports[author_id][index]
                reply += report.summary()
                await message.channel.send(reply)

                report.state = State.AWAITING_REVIEW

                responses = await self.reports[author_id].handle_message(message)
                for r in responses:
                    bot_message = await message.channel.send(r)
                
                self.reports[author_id].message = bot_message

                # handle reactions
                if self.reports[author_id].reaction_mode:
                    if (self.reports[author_id].state == State.AWAITING_REVIEW):
                        for _ in range(Moderator.SEVERITY_LEVELS):
                            await bot_message.add_reaction(self.NUMBERS[_])

                return

    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)