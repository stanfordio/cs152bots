# bot.py
import discord
from discord.ext import commands
from unidecode import unidecode
import csam_text_classification as ctc
import os
import json
import logging
import re
import requests
from report import Report, ModReport
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
    openai_org = tokens['openai_org']
    openai_key = tokens['openai_key']

def csam_detector(message):
    return ctc.content_check(unidecode(message), openai_org, openai_key)

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
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
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            abuse_report = self.reports[author_id].return_abuse_report()
            # send each string in the abuse report to the mod channel
            mod_channel = self.mod_channel
            for abuse_report_string in abuse_report:
                await mod_channel.send(abuse_report_string)
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        # if not message.channel.name == f'group-{self.group_num}':
        #     return
        responses = []
        # Forward the message to the mod channel if and only if it's not in the mod channel already.
        # if message.channel.name == f'group-{self.group_num}':
            # mod_channel = self.mod_channels[message.guild.id]
            # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        banned_user = message.author.name
        # For now we are going to use this as a placeholder until Milestone 3. 
        if (csam_detector(message.content)): # REPLACE in milestone 3 with image hashset or link list etc.
            # await message.delete()
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            await mod_channel.send(f"Our CSAM detection tool has flagged {banned_user} due to detected CSAM. Is the above message CSAM?")
            # TODO(sammym): finish this flow tomorrow
            return
        
        # if (message.content.lower() == "report"):
            # If we don't currently have an active report for this user, add one
        if banned_user not in self.reports:
            self.reports[banned_user] = ModReport(self)
        elif self.reports[banned_user].report_complete():
            self.reports.pop(banned_user)
            self.reports[banned_user] = ModReport(self)

            # #User Report Flow
            # responses = await self.reports[banned_user].handle_message(message)
            # for r in responses:
            #     await message.channel.send(r)

            #Moderator Report Handling
        responses = await self.reports[banned_user].handle_mod_message(message)
        for r in responses:
            await self.mod_channels[message.guild.id].send(r)
            # scores = self.eval_text(message.content)
            # await mod_channel.send(self.code_format(scores))

    async def on_message_edit(self, before, after):
        if before.content != after.content:
            if csam_detector(after.content):
                await after.delete()
                await self.mod_channels[after.guild.id].send(f"We have banned user {after.author.name}, reported to NCMEC and removed the content.")
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


bot = ModBot()
bot.run(discord_token)