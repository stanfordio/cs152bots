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
        self.reports = {} # Map from user IDs to the state of their report
        
        self.awaiting_mod_decisions = {1: {}, 2: {}, 3:{}, 4:{}, 5:{}} # Maps from abuse types to a list of tuples containing report id, the message object, and images
        self.caseno_to_info = {} # Maps from report id to a tuple defined below
        self.most_recent = None

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
        if message.guild and message.guild.id in self.mod_channels:
            await self.handle_mod_message(message)
        if message.guild:
            # print(self.mod_channels[message.guild.id])
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
        author = message.author

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
            
            if self.reports[author_id].requires_forwarding:
                msg = self.reports[author_id].message
                mod_channel = self.mod_channels[msg.guild.id]
                start_message = '=' * 20 + '\n'
                start_message += '****REPORT START****\n' 
                start_message += f'REPORT ID: {self.reports[author_id].report_no}\n'
                start_message += f"Forwarded report from {author}\n"
                start_message += f"Message text: {msg.content}\n"
                start_message += f'Author of the message: {msg.author.name}\n'
                start_message += f"Abuse type: {self.reports[author_id].forward_abuse_string}\n"
                if self.reports[author_id].specific_abuse_string:
                    start_message += f"Specific abuse: {self.reports[author_id].specific_abuse_string}\n"
                if not self.reports[author_id].keep_AI:
                    start_message += "The user would like to not see AI-generated content anymore.\n"
                
                image = None
                if msg.attachments:
                    attachment = msg.attachments[0]  # Assuming the first attachment is the image
                    start_message += 'Image associated with the message attached:\n'
                    image = attachment
                elif msg.embeds:
                    embed = msg.embeds[0]
                    start_message += 'Embed associated with the message attached:\n'
                    image = embed
                end_message = f'MODERATORS PLEASE SELECT 1. Ignore 2. Warn 3. Delete 4. Ban 5. Delete + Warn 6. Delete + Ban\n'
                end_message += '****REPORT END****\n'
                end_message += '=' * 20
                
                # maps from abuse type ot report number to a tuple of the starting message we send to the mod server, images, the ending message for the mod server, and the actual message in question.
                # the last two are for ease of cleaning up the report dicionary once it is handled.
                self.awaiting_mod_decisions[self.reports[author_id].abuse_type][self.reports[author_id].report_no] = (start_message, image, end_message, msg, self.reports[author_id].abuse_type, self.reports[author_id].report_no)
                self.caseno_to_info[self.reports[author_id].report_no] = (start_message, image, end_message, msg, self.reports[author_id].abuse_type, self.reports[author_id].report_no)
                
                self.most_recent = (start_message, image, end_message, msg, self.reports[author_id].abuse_type, self.reports[author_id].report_no)
                
                await mod_channel.send('Most recent report added to the queue for review:\n')
                await mod_channel.send(start_message)
                if image:
                    await mod_channel.send(file=await image.to_file())
                await mod_channel.send(end_message)
                # await mod_channel.send(end_message)
            
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
    
    async def handle_mod_message(self, message):
        # will handle the moderators' decisions
        if not message.channel.name == f'group-{self.group_num}-mod':
            return
        
        # print(message.content)
        message_content = message.content.split()
        if message_content[0] != 'RETRIEVE' and message_content[0] != 'EXECUTE':
            return_message = 'Invalid command. Please type RETRIEVE followed by a case number, \'MOST RECENT\' or \'HIGH PRIORITY\' to retrieve a case or EXECUTE followed by a case number, target, and action to close a case.'
            await message.channel.send(return_message)
        
        if message_content[0] == 'RETRIEVE' and 'MOST RECENT' not in message.content.upper() and 'HIGH PRIORITY' not in message.content.upper():
            try:
                case_number = int(message_content[1])
                case_number = '#' + str(case_number)
                abuse_type = None
                for key in self.awaiting_mod_decisions:
                    if case_number in self.awaiting_mod_decisions[key]:
                        abuse_type = key
                        break
                if abuse_type:
                    package = self.awaiting_mod_decisions[abuse_type][case_number]
                    await message.channel.send(package[0])
                    if package[1]:
                        await message.channel.send(file=await package[1].to_file())
                    await message.channel.send(package[2])
                else:
                    await message.channel.send('Case not found.')
            except:
                await message.channel.send('Invalid case number.')
        elif message_content[0] == 'RETRIEVE' and 'MOST RECENT' in message.content.upper():
            if self.most_recent:
                package = self.most_recent
                await message.channel.send(package[0])
                if package[1]:
                    await message.channel.send(file=await package[1].to_file())
                await message.channel.send(package[2])
            else:
                await message.channel.send('No cases found.')
        elif message_content[0] == 'RETRIEVE' and 'HIGH PRIORITY' in message.content.upper():
            # abuse 1 and 2 are high priority, the rest are not
            for key in range(1, 3):
                if self.awaiting_mod_decisions[key]:
                    package = self.awaiting_mod_decisions[key][min(self.awaiting_mod_decisions[key].keys())]
                    await message.channel.send(package[0])
                    if package[1]:
                        await message.channel.send(file=await package[1].to_file())
                    await message.channel.send(package[2])
                    break
            else:
                await message.channel.send('No high priority cases found.')
        
        elif message.content[0] == 'EXECUTE':
            #TODO: IMPLEMENT THIS WITH THE MODERATOR FLOW
            pass
        

    
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