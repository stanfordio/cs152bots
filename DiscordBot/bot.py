# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, BotReactMessage
import pdb

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


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.flagged_users = {} # Map of users that have been flagged to users that have flagged them (for moderator review)

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
    
    async def on_raw_reaction_add(self, payload):
        # Only look for reacts in the DMs 
        if not payload.guild_id:
            await self.handle_dm_react(payload)

    async def handle_dm_react(self, payload):
        author_id = payload.user_id
        message_id = payload.message_id
        responses = []
        logger.info(payload.emoji)
        logger.info(str(payload.emoji.name))

        # Only respond to reacts if they're part of a reporting flow
        if author_id not in self.reports or message_id not in self.reports[author_id].reporting_message_ids:
            logger.info("message id " + str(message_id) + " not in reports")
            return
        
        channel = await self.fetch_channel(payload.channel_id)
        responses = await self.reports[author_id].handle_react(payload)
        for r in responses:
            if not r:
                continue
            # If response prompts user for further action, save the message id
            if r.startswith("You reported fraud. Please react"):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.FRAUD_LEVEL
            elif r.startswith("You reported his person has asked you for money. Please react"):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.MONEY_LEVEL
            elif r.startswith("Thank you for reporting."):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.BLOCK_LEVEL
            else:
                await channel.send(r)


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

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            # If response prompts user for further action, save the message id
            if "Please react with one or more of the following to specify a reason for this report" in r:
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.FIRST_LEVEL
            elif r.startswith("Thank you for reporting."):
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.BLOCK_LEVEL
            elif r.startswith("You selected other."):
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.OTHER_THREAD
            else:
                await message.channel.send(r)

        # If the report is canceled, remove it from our map
        if self.reports[author_id].report_canceled():
            self.reports.pop(author_id)

        # If the report is complete, remove it from our map but flag the reported user
        if self.reports[author_id].report_complete():
            self.flagged_users[reported_user_id] = (author_id, self.reports[author_id].reported_issues)
            #TODO: do something with this information (maybe more for milesotne 3)
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    
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
