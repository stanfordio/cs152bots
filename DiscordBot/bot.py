# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, ModerationRequest
import pdb
from discord.ext import context
from perspective import perspective_spam_prob
from gpt4_response import gpt4_warning
from moderation import Moderation_Flow

NOT_SPAM_THRESH_HOLD = .5
SPAM_THRESH_HOLD = .904
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


class ModBot(context.ContextClient, discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report

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
        
        print (self.mod_channels)

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
            await self.check_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        print("entering handle dm")
        author_id = message.author.id
        if author_id in self.reports and self.reports[author_id].report_complete():
            # If the report is complete we want to send it to our 
            self.reports.pop(author_id)
        

        # TODO: Super important: We ignore messages that are currently filling out reports
        if author_id in self.reports:
            return
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

        ## Let the report class handle this message
        report = await self.reports[author_id].handle_message(message)

        # If the report is complete we want to send it to our 
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)
            await self.send_report_to_mod_channel(report)

    # Send report to moderation channel
    async def send_report_to_mod_channel(self, report: ModerationRequest):
        message = report.message
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(report.print_report())
        mod_flow = Moderation_Flow(report.message, mod_channel)
        mod_flow.handle_moderation_report()
        

    async def check_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        spam_score = self.eval_text(message)

        # if below threshold we can ignore the message
        if spam_score < NOT_SPAM_THRESH_HOLD:
            return

        mod_channel = self.mod_channels[message.guild.id]
        # Here we send the user a warning about why the message can be dangerous
        # TODO: change this back
        # warning = gpt4_warning(message.content) 
        print("Finished generating gpt4 response")
        warning_message = "This message may be a possible scam. Take the following information into consideration: \n" #+ warning
        await message.channel.send(warning_message, reference=message)
        print("warning message sending")

        if spam_score > SPAM_THRESH_HOLD:
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            print_str = "Automated Moderation Report:\n"
            print_str += "Author: " + message.author.name + "\n"
            print_str += "Message: " + message.content + "\n"
            print_str += "Spam Score: " + str(spam_score) + "\n"
            await mod_channel.send(print_str)
            mod_flow = Moderation_Flow(message, mod_channel, True)
            await mod_flow.handle_moderation_report()
            

    def eval_text(self, message):
        content = message.content
        print(content)
        spam_p = float(perspective_spam_prob(content))
        print("Checking message with spam score of: ", spam_p)
        return spam_p

client = ModBot()
client.run(discord_token)