import discord
from discord.ext import commands
import os
import json
import logging
import re
import openai
import sqlite3
from datetime import datetime
from report import Report, State
from mod import Review
import heapq
import heapq

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.openai = openai.OpenAI(
            api_key='sample-api-key')
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.db_connection = sqlite3.connect('mod_db.sqlite')
        self.reviews = {}  # Add a dictionary to keep track of reviews per user
        self.reports = {}
        self.reports_to_review = []
        self.reports = {}
        self.reports_to_review = []

        # Create the database schema if it doesn't exist
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reported_user_id INTEGER,
                reporter_user_id INTEGER,
                reportee TEXT,
                reported_user TEXT,
                reported_message TEXT,
                report_category TEXT,
                report_subcategory TEXT,
                additional_details TEXT,
                priority INTEGER,
                report_status TEXT DEFAULT 'pending',
                time_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker_user_id INTEGER,
                blocked_user_id INTEGER,
                time_blocked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                ban_id INTEGER PRIMARY KEY AUTOINCREMENT,
                banned_user_id INTEGER,
                moderator_user_id INTEGER,
                time_banned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db_connection.commit()

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception(
                "Group number not found in bot's name. Name format should be \"Group # Bot\".")

        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return

        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `block` command to begin the blocking process.\n"
            reply += "Use the `unblock` command to unblock a user.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)
        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Check command
        # Check command
        command = message.content.split()[0]
        if command == Report.START_KEYWORD:
            responses = await self.reports[author_id].handle_message(message)
            responses = await self.reports[author_id].handle_message(message)
        elif command == Report.BLOCK_KEYWORD:
            responses = await self.reports[author_id].handle_block(message)
        elif command == Report.UNBLOCK_KEYWORD:
            responses = await self.reports[author_id].handle_unblock(message)
        else:
            if author_id in self.reports:
                if self.reports[author_id].state == State.AWAITING_UNBLOCK:
                    responses = await self.reports[author_id].handle_unblock_confirm(message)
                else:
                    responses = await self.reports[author_id].handle_message(message)
                    blocks = await self.reports[author_id].handle_block(message)
                    responses.extend(blocks)

        # Send all responses
        if responses:
            for r in responses:
                await message.channel.send(r)

        # If the report/block is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete() or self.reports[author_id].block_complete():
            heapq.heappush(self.reports_to_review,
                           (self.reports[author_id].priority, self.reports[author_id]))
            self.reports.pop(author_id)

    async def handle_start_review(self, message):
        author_id = message.author.id
        if author_id not in self.reviews:
            self.reviews[author_id] = Review(self)
        responses = await self.reviews[author_id].handle_review(message)
        return responses

    async def handle_unban_review(self, message):
        author_id = message.author.id
        if author_id not in self.reviews:
            self.reviews[author_id] = Review(self)
        responses = await self.reviews[author_id].handle_unban(message)
        return responses

    async def handle_channel_message(self, message):
        if not (message.channel.name == f'group-{self.group_num}' or message.channel.name == f'group-{self.group_num}-mod'):
            return

        author_id = message.author.id
        responses = []

        if message.channel.name == f'group-{self.group_num}-mod':
            if message.content.split()[0] == Review.START_KEYWORD:
                if author_id not in self.reviews:
                    self.reviews[author_id] = Review(self)
                responses = await self.reviews[author_id].handle_review(message)
            elif message.content.split()[0] == Review.UNBAN_KEYWORD:
                responses = await self.handle_unban_review(message)
            elif author_id in self.reviews:
                responses = await self.reviews[author_id].handle_review(message)
        else:
            flag_type = await self.evaluate_message(message.content)
            if flag_type:
                await self.handle_offensive_message(message, flag_type)
            else:
                mod_channel = self.mod_channels[message.guild.id]
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')

        if responses:
            for r in responses:
                await message.channel.send(r)

    def eval_text(self, message):
        return message

    def code_format(self, text):
        return "Evaluated: '" + text + "'"

    async def evaluate_message(self, message_content):
        response = self.openai.moderations.create(input=message_content)
        output = response.results[0]

        if output.flagged:
            print(f"Flagged content: {message_content}")
            print(f"Output: {output}")

            flagged_categories = [
                category for category, flagged in output.categories.dict().items() if flagged]

            if flagged_categories:
                return flagged_categories[0]
        return None

    async def generate_report(self, message, flag_type):
        report = Report(self)
        report.reported_user_id = message.author.id
        report.report_category = flag_type.upper()
        report.reportee = "System"
        report.reporter_user_id = self.user.id
        report.reported_user = message.author.name
        report.reported_message = message.content
        report.time_reported = datetime.now()
        report.additional_details = "Flagged by OpenAI"
        report.report_subcategory = "N/A"  # TODO: Add subcategory to report
        report.report_status = "pending"

        # set priority based on flag type
        # Flag types from OpenAI: ['hate, hate/threatening, harassment,
        # harassment/threatening, harassment/threatening, self-harm,
        # self-harm/intent, self-harm/instructions
        # sexual, sexual/minors, violence, violence/graphic

        if flag_type == 'hate/threatening' or flag_type == 'harassment/threatening' or flag_type == 'self-harm/intent' or flag_type == 'sexual/minors' or flag_type == 'violence/graphic' or flag_type == "self-harm/intent" or flag_type == "self-harm/instructions" or flag_type == "violence" or flag_type == "violence/graphic":
            report.priority = 1
        else:
            report.priority = 2

        report.save_report(self.db_cursor, self.db_connection)

        mod_channel = self.mod_channels.get(message.guild.id)
        if mod_channel:
            await mod_channel.send(
                f"🚩 **Report Generated** 🚩\n"
                f"**User:** {message.author.name}\n"
                f"**Reason:** {flag_type}\n"
                f"**Message:** {message.content}\n"
                f"**Time:** {report.time_reported.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            logger.warning("No mod channel found for the guild.")
        report.save_report(self.db_cursor, self.db_connection)

    async def handle_offensive_message(self, message, flag_type):
        await message.delete()

        await message.author.send(
            f"Your message in {message.channel.name} was removed because it was flagged as {flag_type}. "
            "Please be mindful of the community guidelines."
        )

        await self.generate_report(message, flag_type)


client = ModBot()
client.run(discord_token)
