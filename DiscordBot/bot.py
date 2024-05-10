# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
from moderate import Moderate


# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# violations = {}

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
        self.reports = {} # Map from user IDs to the state of their report
        self.HANDLING_REPORT = False
        self.current_moderation = None
        self.violations = {} # Map from offender user IDs to the number of offenses 

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
            
             # adding the offender to the global violations dictionary    
            # offender_id = self.reports[author_id].reported_message['content'].author.id
            # if offender_id in self.violations:
            #     self.violations[offender_id] += 1
            # else:
            #     self.violations[offender_id] = 1
                

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            if r.startswith("I found this message"):
                offender_id = self.reports[author_id].reported_message['content'].author.id
                if offender_id in self.violations:
                    self.violations[offender_id] += 1
                else:
                    self.violations[offender_id] = 1
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if message.channel.name == f'group-{self.group_num}':
            return
        else:
            await self.handle_mod_channel_message(message)
              
    async def handle_mod_channel_message(self, message):
        mod_channel = self.mod_channels[message.guild.id]
        
        if self.HANDLING_REPORT:
            reply = await self.current_moderation.moderate_content(message.content)

            await mod_channel.send(reply)
            if self.current_moderation.current_step == 3:
                print("Made it into the curerent moderation step is step 3")
                self.HANDLING_REPORT == False
                print("Handling report is now set to false")


        elif message.content.lower() == 'handle report':
            if not self.reports:
                await mod_channel.send(f'There are currently 0 reports.')     
                return

            id, report = next(iter(self.reports.items()))
            await mod_channel.send(f"Now handling user's {id} report:")
            self.reports.pop(id)
            await mod_channel.send(f'ID {id}, Message: {report.reported_message["content"]}')
            self.current_moderation = Moderate(mod_channel, id, report, self.violations)
            self.HANDLING_REPORT = True
            await mod_channel.send(f'Is this hateful conduct? Please say `yes` or `no`.')

        else:
            await mod_channel.send("Please type 'handle report' to see oldest report.")
            await mod_channel.send(f'There are {len(self.reports)} reports pending.')




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