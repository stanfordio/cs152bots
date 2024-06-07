# bot.py
import discord
import os
import json
import logging
import re
from text_classifier import classify_text
from report import Report
from moderator import ModeratorReport
from supabase_client import SupabaseClient

supabase = SupabaseClient()

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
    subscription_key = tokens['SUBSCRIPTION_KEY']
    project_name = tokens['PROJECT_NAME']
    deployment_name = tokens['DEPLOYMENT_NAME']
    endpoint = tokens['ENDPOINT']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.mod = None
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

    async def handle_dm(self, message):
        logger.log(logging.INFO, f"Received DM from {message.author.name}: {message.content}")
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
            reply = "I am sorry, I cannot understand you. Please use the `help` command for instructions."
            await message.channel.send(reply)
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
        logger.log(logging.INFO, f"Received message in channel {message.channel.name} from {message.author.name}: {message.content}")
        # Check if the message is in the moderator channel
        if message.channel.name == f'group-{self.group_num}-mod':
            logger.log(logging.INFO,f"Received message in mod channel: {message.content}")
            # Ignore messages from the bot
            if message.author.id == self.user.id:
                return
    
            # Only respond to messages if they're part of a reporting flow
            if not self.mod and not message.content.startswith(ModeratorReport.START_KEYWORD):
                return

            # If we don't currently have an active report for this user, add one
            if not self.mod:
                self.mod = ModeratorReport(client, message)
            
            moderator_report = self.mod
            if message.content == ModeratorReport.START_KEYWORD:
                # Let the report class handle this message; forward all the messages it returns to us
                # TODO: get highest priority report
                responses = await moderator_report.handle_report(message)
                for r in responses:
                    await message.channel.send(r)
            else:
                responses = await moderator_report.handle_report(message)
                for r in responses:
                    await message.channel.send(r)
            return
        else:
            # if user has been banned, delete the message
            if supabase.is_user_banned(message.author.id):
                await message.delete()
                await message.channel.send(f"*Message has been deleted because the user `@{message.author.name}` is banned and can no longer send messages to this channel.*")
                return
            # classify messages from non-moderator channels
            classification_result = await classify_text(message.content, subscription_key, project_name, deployment_name, endpoint)
            await self.process_classification_results(message, classification_result)

    async def process_classification_results(self, message, classification_result):
        try:
            for task in classification_result['tasks']['items']:
                if task['status'] == 'succeeded':
                    for doc in task['results']['documents']:
                        for cls in doc['class']:
                            if cls['category'] == 'predatory':
                                if cls['confidenceScore'] >= 0.95:
                                    # High confidence predatory content: send warning message and report
                                    logger.log(logging.INFO, f"Confidence score of {cls['confidenceScore']}. Sending warning to user and reporting.")
                                    await self.report_predatory_content(message, cls['confidenceScore'], True)
                                    
                                else:
                                    # Lower confidence predatory content: report but do not send warning
                                    logger.log(logging.INFO, f"Confidence score of {cls['confidenceScore']}. Reporting potentially harmful content for review.")
                                    await self.report_predatory_content(message, cls['confidenceScore'], False)
        except Exception as e:
            logger.error(f"Failed to process classification results: {e}")

    async def report_predatory_content(self, message, score, high_confidence):
        mod_channel = self.mod_channels.get(message.guild.id)
        if mod_channel:
            report_message = f"Detected potentially predatory content from `{message.author.display_name}` with confidence ({score:.2f}). Review needed."
            await mod_channel.send(report_message)
            #TODO add to the queue instead
            if high_confidence:
                supabase.increment_num_reports_received(message.author.id)
                # send notification to the original channel where the message was detected
                notification_msg = f"Warning: The following message was forwarded to the moderators as it potentially violates our Community Standards regarding Child Sexual Exploitation, Abuse, and Nudity:\n```{message.content}```\n\n"
                await message.channel.send(notification_msg)

            # Send warning to the reported user in private
            user_warning_msg = f"Warning: Your message in {message.channel.mention} was forwarded to moderators as it potentially violates our community standards regarding Child Sexual Exploitation, Abuse, and Nudity. The content of the message was:\n```{message.content}```\n\n"
            await message.author.send(user_warning_msg)
    
client = ModBot()
client.run(discord_token)