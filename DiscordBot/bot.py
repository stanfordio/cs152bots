# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, AbuseType, MisinfoCategory, HealthCategory, NewsCategory
from user_stats import UserStats
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
        intents.members = True  # Add members intent
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.active_mod_flow = None # State for the current moderation flow
        self.user_stats = UserStats() # Initialize user statistics tracking

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

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#-mod" channel
        if message.channel.name == f'group-{self.group_num}-mod':
            await self.handle_mod_channel_message(message)
        elif message.channel.name == f'group-{self.group_num}':
            return

    async def start_moderation_flow(self, report_type, report_content, message_author, message_link=None):
        # Determine the initial step based on report type
        if report_type.startswith('ADVERTISING MISINFO'):
            initial_step = 'advertising_done'
        elif report_type.startswith('MISINFORMATION') or report_type.startswith('HEALTH MISINFO') or report_type.startswith('NEWS MISINFO'):
            initial_step = 'danger_level'
        else:
            initial_step = 'default_done'
        self.active_mod_flow = {
            'step': initial_step,
            'report_type': report_type,
            'report_content': report_content,
            'message_author': message_author,
            'message_link': message_link,
            'context': {}
        }
        mod_channel = None
        for channel in self.mod_channels.values():
            mod_channel = channel
            break
        if mod_channel:
            await mod_channel.send(f"A new report has been submitted:\nType: {report_type}\nContent: {report_content}\nReported user: {message_author}")
            if initial_step == 'danger_level':
                await mod_channel.send("What is the level of danger for this report?\n1. LOW\n2. MEDIUM\n3. HIGH")
            elif initial_step == 'advertising_done':
                await mod_channel.send("Report sent to advertising team. No further action required.")
                self.active_mod_flow = None
            elif initial_step == 'default_done':
                # Just show the report, do not prompt for reply
                self.active_mod_flow = None
            else:
                await self.prompt_next_moderation_step(mod_channel)

    async def notify_reported_user(self, user_name, guild, outcome, explanation=None):
        # Find the user object by name in the guild
        user = discord.utils.get(guild.members, name=user_name)
        if user:
            try:
                msg = f"Your message was reviewed by moderators. Outcome: {outcome}."
                if explanation:
                    msg += f"\nReason: {explanation}"
                msg += "\nIf you believe this was a mistake, you may reply to this message to appeal."
                await user.send(msg)
            except Exception as e:
                print(f"Failed to DM user {user_name}: {e}")

    async def handle_mod_channel_message(self, message):
        if not self.active_mod_flow:
            return
        step = self.active_mod_flow['step']
        ctx = self.active_mod_flow['context']
        content = message.content.strip().lower()
        mod_channel = message.channel
        report_type = self.active_mod_flow['report_type']
        report_content = self.active_mod_flow['report_content']
        reported_user_name = self.active_mod_flow['message_author']
        guild = mod_channel.guild if hasattr(mod_channel, 'guild') else None

        # Get the user ID from the reported user's name
        reported_user = discord.utils.get(guild.members, name=reported_user_name)
        if not reported_user:
            await mod_channel.send(f"Could not find user {reported_user_name}. Please verify the username is correct.")
            return

        # Misinformation moderation flow
        if step == 'advertising_done':
            # Already handled
            self.active_mod_flow = None
            return
        if step == 'danger_level':
            if content not in ['1', '2', '3']:
                await mod_channel.send("Invalid option. Please choose:\n1. LOW\n2. MEDIUM\n3. HIGH")
                return
            danger_levels = {'1': 'low', '2': 'medium', '3': 'high'}
            ctx['danger_level'] = danger_levels[content]
            if content == '1':  # LOW
                await mod_channel.send("Flag post as low danger. After claim is investigated, what action should be taken on post?\n1. DO NOT RECOMMEND\n2. FLAG AS UNPROVEN")
                self.active_mod_flow['step'] = 'low_action_on_post'
                return
            elif content == '2':  # MEDIUM
                await mod_channel.send("Flag post as medium danger. After claim is investigated, what action should be taken on post?\n1. REMOVE\n2. RAISE\n3. REPORT TO AUTHORITIES")
                self.active_mod_flow['step'] = 'medium_action_on_post'
                return
            elif content == '3':  # HIGH
                await mod_channel.send("Flag post as high danger. What emergency action should be taken based on post?\n1. REMOVE\n2. RAISE\n3. REPORT TO AUTHORITIES")
                self.active_mod_flow['step'] = 'high_action_on_post'
                return
        if step == 'low_action_on_post':
            if content not in ['1', '2']:
                await mod_channel.send("Invalid option. Please choose:\n1. DO NOT RECOMMEND\n2. FLAG AS UNPROVEN")
                return
            if content == '1':  # DO NOT RECOMMEND
                await mod_channel.send("Post will not be recommended. Action recorded. (Update algorithm so post is not recommended.)")
                await self.notify_reported_user(reported_user_name, guild, outcome="Post not recommended.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post not recommended"
                )
                self.active_mod_flow = None
                return
            elif content == '2':  # FLAG AS UNPROVEN
                await mod_channel.send("Post will be flagged as unproven/non-scientific. Please add explanation for why post is being flagged.")
                self.active_mod_flow['step'] = 'flag_explanation'
                return
        if step == 'flag_explanation':
            await mod_channel.send(f"Explanation recorded: {message.content}\nFlagged post as not proven.")
            await self.notify_reported_user(reported_user_name, guild, outcome="Post flagged as unproven/non-scientific.", explanation=message.content)
            self.user_stats.add_report(
                reported_user.id,
                report_type,
                report_content,
                "Post flagged as unproven/non-scientific",
                message.content
            )
            self.active_mod_flow = None
            return
        if step == 'medium_action_on_post' or step == 'high_action_on_post':
            if content not in ['1', '2', '3']:
                await mod_channel.send("Invalid option. Please choose:\n1. REMOVE\n2. RAISE\n3. REPORT TO AUTHORITIES")
                return
            if content == '1':  # REMOVE
                await mod_channel.send("Post will be removed. Please add explanation for why post is being removed.")
                self.active_mod_flow['step'] = 'remove_explanation'
                return
            elif content == '2':  # RAISE
                await mod_channel.send("Raising to higher level moderator. Report sent to higher level moderators.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Report raised to higher level moderator"
                )
                self.active_mod_flow = None
                return
            elif content == '3':  # REPORT TO AUTHORITIES
                await mod_channel.send("Reporting to authorities. Report sent to authorities.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Reported to authorities"
                )
                self.active_mod_flow = None
                return
        if step == 'remove_explanation':
            await mod_channel.send(f"Explanation recorded: {message.content}\nPost removed. What action should be taken on the creator of the post?\n1. RECORD INCIDENT\n2. TEMPORARILY MUTE\n3. REMOVE USER")
            ctx['remove_explanation'] = message.content
            await self.notify_reported_user(
                reported_user_name,
                guild,
                outcome="Post removed.",
                explanation=ctx.get('remove_explanation', '')
            )
            self.active_mod_flow['step'] = 'action_on_user'
            return
        if step == 'action_on_user':
            if content not in ['1', '2', '3']:
                await mod_channel.send("Invalid option. Please choose:\n1. RECORD INCIDENT\n2. TEMPORARILY MUTE\n3. REMOVE USER")
                return
            if content == '1':  # RECORD INCIDENT
                await mod_channel.send("Incident recorded for internal use. (Add to internal incident count for user.)")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post removed and incident recorded",
                    ctx.get('remove_explanation', '')
                )
                self.active_mod_flow = None
                return
            elif content == '2':  # TEMPORARILY MUTE
                await mod_channel.send("User will be muted for 24 hours.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post removed and user temporarily muted",
                    ctx.get('remove_explanation', '')
                )
                self.active_mod_flow = None
                return
            elif content == '3':  # REMOVE USER
                await mod_channel.send("User will be removed.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post removed and user removed",
                    ctx.get('remove_explanation', '')
                )
                self.active_mod_flow = None
                return

    async def prompt_next_moderation_step(self, mod_channel):
        await mod_channel.send("Moderator, please review the report and respond with your decision.")

client = ModBot()
client.run(discord_token)