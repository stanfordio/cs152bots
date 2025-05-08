# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
import random

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

    async def _send_report_embed(self, report):
        msg    = report.message
        mod_ch = self.mod_channels.get(report.guild_id)
        if not mod_ch:
            return
        embed = discord.Embed(
            title="🚨 New Report Submitted",
            description=f"User <@{report.author_id}> completed a report.",
            color=discord.Color.red()
        )
        embed.add_field("Category",     report.type_selected or "N/A", inline=True)
        embed.add_field("Subtype",      report.subtype_selected or "N/A", inline=True)
        if msg:
            embed.add_field("Flagged Message", f"{msg.author.name}: {msg.content}", inline=False)
        embed.add_field("AI Suspected?", report.q1_response or "N/A", inline=True)
        embed.add_field("User Blocked?",  report.block_response or "N/A", inline=True)
        await mod_ch.send(embed=embed)

    async def handle_dm(self, message):
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond if it's part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # Always reset report if user says "report"
        if message.content.strip().lower() == Report.START_KEYWORD: 
            self.reports[author_id] = Report(self)

        # If no current report, create one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Handle message VIA SENDING TO REPORT.PY
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        if self.reports[author_id].state == State.REPORT_COMPLETE:
            report = self.reports.pop(author_id)
            await self._send_report_embed(report)
            
    
    # MANUAL REVIEW LOGIC

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return
        
        mod_channel = self.mod_channels.get(message.guild.id)

        if not mod_channel:
            print(f"[DEBUG] No mod channel set for guild {message.guild.name}")
            return
        
        
        #await mod_channel.send(
        #f"🔎 Message flagged for review:\n"
        #f"**Author:** {message.author.name}\n"
        #f"**Content:** {message.content}\n"
        #)

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        if scores > 0:

            embed = discord.Embed(
                title="⚠️ Auto-Flagged Message",
                description=f"Suspect score: {scores:.2%}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Author",  value=message.author.mention, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention,      inline=True)
            embed.add_field(name="Content", value=message.content[:1024],      inline=False)
            await mod_channel.send(embed=embed)
        else:
            # otherwise just post the raw evaluation
            await mod_channel.send(self.code_format(scores))

    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''

        # Returns 0 or 1 for now for demo
        return random.getrandbits(1)

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + str(text)+ "'"


client = ModBot()
client.run(discord_token)