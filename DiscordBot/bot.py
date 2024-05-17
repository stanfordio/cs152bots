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
import openai
import datetime
import sqlite3

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
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        # openai integration
        self.openai = openai.OpenAI(
            api_key='sample-api-key')
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.reviews = {}
        self.reports_to_review = []

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
            raise Exception(
                "Group number not found in bot's name. Name format should be \"Group # Bot\".")

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
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `block` command to begin the blocking process.\n"
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

        # Check command
        command = message.content.split()[0]
        if command == Report.START_KEYWORD:
            responses = await self.reports[author_id].handle_message(message)
        elif command == Report.BLOCK_KEYWORD:
            blocks = await self.reports[author_id].handle_block(message)
        else:
            # If it's neither, it might still be in the middle of an ongoing report/block process
            if author_id in self.reports:
                responses = await self.reports[author_id].handle_message(message)
                blocks = await self.reports[author_id].handle_block(message)

        if responses:
            for r in responses:
                await message.channel.send(r)
        if blocks:
            for b in blocks:
                await message.channel.send(b)

        # If the report/block is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete() or self.reports[author_id].block_complete():
            heapq.heappush(self.reports_to_review,
                           (self.reports[author_id].priority, self.reports[author_id]))
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" or "group-#-mod" channel
        if not (message.channel.name == f'group-{self.group_num}' or message.channel.name == f'group-{self.group_num}-mod'):
            return

        author_id = message.author.id
        responses = []

        # Check for specific command in mod channel or process general review in either channel
        if message.channel.name == f'group-{self.group_num}-mod':
            if message.content.split()[0] == Review.START_KEYWORD:
                responses = await self.reviews[author_id].handle_review(message)
            elif author_id in self.reviews:
                responses = await self.reviews[author_id].handle_review(message)
        else:
            # Evaluate message using OpenAI moderation endpoint for the main channel
            flag_type = await self.evaluate_message(message.content)
            if flag_type:
                await self.handle_offensive_message(message, flag_type)
            else:
                mod_channel = self.mod_channels[message.guild.id]
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')

        # Send responses from the review process
        if responses:
            for r in responses:
                await message.channel.send(r)

        # Forward the message to the mod channel
        # mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        # scores = self.eval_text(message.content)
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
        return "Evaluated: '" + text + "'"

    async def automated_evaluate_message(self, message_content):
        response = self.openai.moderations.create(input=message_content)
        output = response.results[0]

        # Check if the content is flagged
        if output.flagged:
            print(f"Flagged content: {message_content}")
            print(f"Output: {output}")
            # Check which categories are flagged
            flagged_categories = [
                category for category, flagged in output.categories.dict().items() if flagged]

            # Return the first flagged category as the flag type
            if flagged_categories:
                return flagged_categories[0]
        return None

    async def generate_report(self, message, flag_type):
        """
        Automatically generate a report for flagged messages.
        Args:
            message (discord.Message): The Discord message object.
            flag_type (str): The type of offense that was detected.
        """
        # Initialize a new report
        report = Report(self)
        report.reported_message = message
        report.reported_user = message.author
        report.time_reported = datetime.datetime.now()
        # Map flag_type to your specific categories if needed
        report.report_category = flag_type
        # TODO: Use OpenAI to get subcategory
        report.report_subcategory = None  # Use custom openAi prompt to get subcategory

        # Assuming we decide categories based on flag_type
        if flag_type == "spam":
            report.report_subcategory = "Spam"
        elif flag_type == "hate_speech":
            report.report_subcategory = "Hate Speech"
        # Add other categories as needed

        # Log the creation of the report to the console or a file
        logger.info(
            f"Generated report for {message.author.name} for {flag_type}")

    # Save the report to the database
        report_id = report.save()
        if report_id:
            logger.info(
                f"Report generated and saved with ID {report_id} for {message.author.name} due to {flag_type}")
        else:
            logger.error("Failed to save the report to the database.")
            return

        # Send a message to the mod channel with details
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

        self.reports[message.author.id] = report

    async def handle_offensive_message(self, message, flag_type):
        """
        Handle messages that have been flagged as offensive.
        Deletes the message and notifies the user.
        Args:
            message (discord.Message): The message to be handled.
            flag_type (str): The type of offense that was detected.
        """
        # Delete the message from the channel
        await message.delete()

        # Send a direct message to the author
        await message.author.send(
            f"Your message in {message.channel.name} was removed because it was flagged as {flag_type}. "
            "Please be mindful of the community guidelines."
        )

        # Generate a report for the incident
        await self.generate_report(message, flag_type)


client = ModBot()
client.run(discord_token)
