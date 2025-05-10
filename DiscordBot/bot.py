# bot.py
import discord
import os
import json
import logging
import re
import requests
import random
from review import Review, ReviewState 
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

        # self.strikes = {} will implement this in later Milestone 3 probably
        self.flagged = {}
        self.reviews = {}
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

    # Helper function for sending reports as embed links to the mod channel. 
    async def send_report_embed(self, report):
        msg    = report.message
        mod_ch = self.mod_channels.get(report.guild_id)
        jump_url = None
        guild_id   = msg.guild.id
        channel_id = msg.channel.id
        message_id = msg.id
        jump_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
 
        embed.add_field("Flagged Message",f"{msg.author.name}: {msg.content}",inline=False)
        # add the jump link
        embed.add_field(
            "Jump to Message",
            f"[Click here to view original message]({jump_url})",
            inline=False
        )
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
        embed.set_footer(text=f"Report ID: {mod_msg.id}")
        self.flagged[mod_msg.id] = report
        mod_msg = await mod_ch.send(embed=embed)
        

    # 
    async def handle_dm(self, message):
        '''
        This function is called whenever a message is sent in the DMs 
        Users start the reporitngp process with the 'report' keyword, which is sent to the moderator channel.
        '''
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

        # ****** Once a user submits their report, it's submitted as an embed to the mod channel ******
        if self.reports[author_id].state == State.REPORT_COMPLETE:
            report = self.reports.pop(author_id)
            await self.send_report_embed(report)
            
            
    async def handle_channel_message(self, message):
        '''
        This function is called for handling user reports as well as automatically flagged posts. Includes automatic flagging, which is currently
        a 50% chance right now for the demo. Moderators can initiate the review process, which calls on review.py, to review posts that have been
        either auto-flagged or user-reported. Deletes the message of the user if the moderator decides that is the correct decision and simulates banning.
        '''
        group_name = f'group-{self.group_num}'
        mod_name   = f'{group_name}-mod'
        channel_name = message.channel.name
        mod_channel = self.mod_channels.get(message.guild.id)

        if channel_name == mod_name:
            author = message.author.id
            text   = message.content.strip().lower()
            # help
            if text == Review.HELP_KEYWORD:
                reply  = "Use the `review <report_message_url>` command to begin the manual review process.\n"
                reply += "Use the `cancel` command to cancel the review process.\n"
                return await mod_channel.send(reply)

            if text.startswith("review"):
                parts = text.split(maxsplit=1)
                if len(parts) != 2:
                    return await mod_channel.send("❌ Usage: `review <embed_id|url>`")
                
                # pull the trailing digits
                m = re.search(r'(\d+)$', parts[1].strip())
                if not m:
                    return await mod_channel.send("❌ Couldn't find an ID in that input.")
                embed_id = int(m.group(1))

                # lookup
                report_obj = self.flagged.get(embed_id)
                if not report_obj:
                    return await mod_channel.send(f"❌ No report found with ID `{embed_id}`.")

                # instantiate & stash
                rev = Review(self, report=report_obj)
                self.reviews[message.author.id] = rev

                # fire off first prompt via handle_message
                responses = await rev.handle_message(message)
                for line in responses:
                    await mod_channel.send(line)
                return

            # ongoing review flow
            if author in self.reviews:
                resp = await self.reviews[author].handle_message(message)
                for line in resp:
                    await mod_channel.send(line)
                if self.reviews[author].state == ReviewState.REVIEW_COMPLETE:
                    if self.reviews[author].q1_response == "yes":
                        await self.reviews[author].message.delete()
                        await mod_channel.send("Deleted user's message.")
                    if self.reviews[author].q2_response == "yes":
                        await mod_channel.send("Removed user from the server")
                    del self.reviews[author]
                return
            return 

        # AUTO FLAGGING CODE
        elif channel_name == group_name:
        # forward raw text to mods
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            scores = self.eval_text(message.content)

            if scores > 0:
                # build jump link
                jump_url = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                auto_report = Report(self)
                auto_report.message         = message
                auto_report.type_selected   = "automated"
                auto_report.subtype_selected = "suspect_content"
                auto_report.author_id       = message.author.id
                auto_report.guild_id        = message.guild.id

                embed = discord.Embed(
                    title="Auto-Flagged Message",
                    description=f"Suspect score: {scores:.2%}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Author",  value=message.author.mention, inline=True)
                embed.add_field(name="Channel", value=message.channel.mention,      inline=True)
                embed.add_field(name="Content", value=message.content[:1024],      inline=False)
                embed.add_field(
                    name="Jump to Message",
                    value=f"[Click here to view original message]({jump_url})",
                    inline=False
                )
                embed.add_field(
                        name="Message Link",
                        # inline code span prevents auto-linking
                        value=f"`{jump_url}`",
                        inline=True
                    )
                
                mod_msg = await mod_channel.send(embed=embed)
                self.flagged[mod_msg.id] = auto_report

            else:
                await mod_channel.send(self.code_format(scores))

    def eval_text(self, message):
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