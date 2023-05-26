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
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        # self.reports = {} # Map from user IDs to the state of their report
        self.reports = [] # list of outstanding reports
        self.curr_report = None # Sets the Report currently being handled by moderator
        self.curr_report_idx = None
        self.warned_users = set()  # Set of users who have been warned for adult nudity

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
                    self.mod_channel = channel
        

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

    async def handle_dm(self, message):
        # mod_channel = self.mod_channels[message.guild.id]
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        elif message.content == Report.QUEUE_KEYWORD:
            reply = "Moderation process started.\n\n"
            reply += "Here are the current reported messages in the queue:\n"
            for idx, report in enumerate(self.reports):
                # reply += f"{idx}: `{report.message.content}`\n"
                reply += f"{idx}: `{report.message.content}` {report.link}\n"
            reply += "\nPlease enter the number for the message you wish to address."
            await message.channel.send(reply)
            return

        # moderator choosing a message to address
        elif message.content.isnumeric():
            idx = int(message.content)
            if len(self.reports) != 0 and 0 <= idx < len(self.reports):
                target = self.reports[idx]

                # designate current message being moderated
                self.curr_report = target
                self.curr_report_idx = idx
                await self.mod_channel.send(f"Report checked out: \n{self.curr_report.message.author}: `{self.curr_report.message.content}`")
                responses = await target.moderate(target.message)
                for r in responses:
                    await message.channel.send(r)
        
        # moderator addressing a message
        elif message.content == "valid":
            if self.curr_report.state == State.CSAM:
                await self.mod_channel.send(f"Deleted by moderator: \n{self.curr_report.message.author}: `{self.curr_report.message.content}`")
                await self.curr_report.message.delete()
                reply = "The message has been removed, the user has been banned, and NCMEC has been notified. Thank you!"
                await message.channel.send(reply)
                del self.reports[self.curr_report_idx]
                self.curr_report = None
                self.curr_report_idx = None
                # self.reports.pop(self.curr_reporter)
                return
            
            if self.curr_report.state == State.ADULT:
                await self.mod_channel.send(f"Deleted by moderator: \n{self.curr_report.message.author}: `{self.curr_report.message.content}`")
                await self.curr_report.message.delete()
                offender = self.curr_report.message.author
                if offender in self.warned_users:
                    reply = "The message has been removed and the user has been banned. Thank you!"
                    await message.channel.send(reply)
                else:
                    self.warned_users.add(offender)
                    reply = "The message has been removed and the user has been warned. Thank you!"
                    await message.channel.send(reply)
                
                del self.reports[self.curr_report_idx]
                self.curr_report = None
                self.curr_report_idx = None
                # self.reports.pop(self.curr_reporter)
                return
        
        elif message.content == "invalid":
            del self.reports[self.curr_report_idx]
            self.curr_report = None
            self.curr_report_idx = None
            # self.reports.pop(self.curr_reporter)
            reply = "Report discarded. Thank you!"
            await message.channel.send(reply)
            return

        else:
            responses = []
            # Only respond to messages if they're part of a reporting flow
            # if not message.content.startswith(Report.START_KEYWORD):
            #     return

            if message.content.startswith(Report.START_KEYWORD):
                self.reports.append(Report(self))
                await self.mod_channel.send(f"Report created - DM me `queue` to view the current report queue.")
                
            # Let the report class handle this message; forward all the messages it returns to us
            if len(self.reports) > 0:
                responses = await self.reports[-1].handle_message(message)
                for r in responses:
                    await message.channel.send(r)

            # If the report is complete or cancelled, remove it from our map
            for idx, report in enumerate(self.reports):
                if report.report_complete():
                    del self.reports[idx]


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        # await mod_channel.send(self.code_format(scores))

    
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
