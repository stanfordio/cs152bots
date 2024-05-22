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
import traceback
import asyncio
import vertexai
from vertexai.generative_models import GenerativeModel


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
        self.require_approval = 1
        self.verify = 0
        self.waiting_mod = 0

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
        try:
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


            ### CURRENTLY TESTING - FEATURE FOR LOGGING REPORTS
            try: 
                mod_channel = None
                for guild in self.guilds:
                    for channel in guild.text_channels:
                        if channel.name == f'group-{self.group_num}-mod':
                            mod_channel = channel

            # If the report is ready to be moderated, send log to moderator in mod-channel
                if self.reports[author_id].report_moderate_ready():
                    ## extract content for logs message
                    report_type, reported_content = self.reports[author_id].get_report_info()
                    reported_guild = reported_content[0]
                    reported_channel = reported_content[1]
                    reported_message = reported_content[2]

                    old_approval_mode = self.require_approval

                    if report_type == "glorification or promotion":
                        self.require_approval = 0
                    

                    ## send logs message
                    reply = "MESSAGE_TO_MODERATOR_LOGS:\n"
                    reply += "Report received violation of type: " + report_type + "\n"
                    reply += "The reported message sent was in this guild: " + str(reported_guild) + "\n"
                    reply += "Sent in channel: " + str(reported_channel) + "\n"
                    reply += "Reported message:" + "```" + reported_message.author.name + ": " + reported_message.content + "```" + "\n-\n-\n"
                    await asyncio.sleep(1)
                    await mod_channel.send(reply)
                    
                    message_to_user = self.reports[author_id].get_moderation_message_to_user()
                    await asyncio.sleep(1)
                    await mod_channel.send(message_to_user)
                    platform_action = self.reports[author_id].get_platform_action()
                    await asyncio.sleep(1)
                    await mod_channel.send(platform_action)

                    await self.seek_verification()        

                    self.require_approval = old_approval_mode

                    self.reports[author_id].end_report()

            except Exception as e:
                # Get the stack trace as a string
                stack_trace = traceback.format_exc()
                
                # Construct the error message with detailed information
                error_message = (
                    "Oops! Something went wrong. Here's the error message and additional details:\n\n"
                    f"Error Type: {type(e).__name__}\n"
                    f"Error Details: {str(e)}\n\n"
                    "Stack Trace:\n"
                    f"{stack_trace}"
                )
                
                # Send the detailed error message to the Discord channel
                await message.channel.send(error_message)
                return

            # If the report is complete or cancelled, remove it from our map
            if self.reports[author_id].report_complete():
                self.reports.pop(author_id)

                
        except Exception as e:
                # Get the stack trace as a string
                stack_trace = traceback.format_exc()
                
                # Construct the error message with detailed information
                error_message = (
                    "Oops! Something went wrong. Here's the error message and additional details:\n\n"
                    f"Error Type: {type(e).__name__}\n"
                    f"Error Details: {str(e)}\n\n"
                    "Stack Trace:\n"
                    f"{stack_trace}"
                )
                
                # Send the detailed error message to the Discord channel
                await message.channel.send(error_message)
                return

    async def handle_channel_message(self, message):
        try:
            mod_channel = self.mod_channels[message.guild.id]
    
            if message.channel.name == f'group-{self.group_num}-mod':

                ### keywords

                if message.content == 'Require moderator':
                    self.require_approval = 1
                    self.waiting_mod = 0
                    reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                    reply += "Moderator manual review now required." + "\n-\n-\n"
                    await asyncio.sleep(1)
                    await mod_channel.send(reply)
                    
                if message.content == "Automatic system review":
                    self.require_approval = 0
                    reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                    reply += "Moderator manual review is now not required." + "\n-\n-\n"
                    await asyncio.sleep(1)
                    await mod_channel.send(reply)

                if self.waiting_mod == 1:
                    if message.content == 'yes':
                        reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                        reply += "Moderator has determined the previous report is indeed in violation of community guidelines. The previous pending actions will be taken." + "\n-\n-\n"
                        self.waiting_mod = 0
                    elif message.content == 'no':
                        reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                        reply += "Moderator has determined the previous report was not in violation of community guidelines. No further action is needed." + "\n-\n-\n"
                        self.waiting_mod = 0
                    else:
                        reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                        reply += "That is not a valid choice; please select 'yes' or 'no'" + "\n-\n-\n"
                    await asyncio.sleep(1)
                    await mod_channel.send(reply)
                    

        except Exception as e:
                # Get the stack trace as a string
                stack_trace = traceback.format_exc()
                
                # Construct the error message with detailed information
                error_message = (
                    "Oops! Something went wrong. Here's the error message and additional details:\n\n"
                    f"Error Type: {type(e).__name__}\n"
                    f"Error Details: {str(e)}\n\n"
                    "Stack Trace:\n"
                    f"{stack_trace}"
                )
                
                # Send the detailed error message to the Discord channel
                await message.channel.send(error_message)
                return


        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        ## gemini prompting
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"

            project_id = "moderation-424102 "  ## for parker's gcloud account, please use responsibly <3
            vertexai.init(project=project_id, location="us-central1")
            model = GenerativeModel(model_name="gemini-1.0-pro-002")
            prompt = "Does the following message seem like it supports the glorification, financing, or promotion of terrorism (yes/no)?" + message.content
            response = model.generate_content(
                prompt
            )
            reply = "GEMINI_REVIEW_FOR_MESSAGE: " + message.content + "\n"
            reply += "Does this message violate our policy? " + response + "\n-\n-\n"
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            await asyncio.sleep(1)
            await mod_channel.send(reply)
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))

        except Exception as e:
                # Get the stack trace as a string
                stack_trace = traceback.format_exc()
                
                # Construct the error message with detailed information
                error_message = (
                    "Oops! Something went wrong. Here's the error message and additional details:\n\n"
                    f"Error Type: {type(e).__name__}\n"
                    f"Error Details: {str(e)}\n\n"
                    "Stack Trace:\n"
                    f"{stack_trace}"
                )
                
                # Send the detailed error message to the Discord channel
                await mod_channel.send(error_message)
                return
        
        ##await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        ##scores = self.eval_text(message.content)
        ##await mod_channel.send(self.code_format(scores))

    
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
    
    async def seek_verification(self):
        try: 
            mod_channel = None
            for guild in self.guilds:
                for channel in guild.text_channels:
                    if channel.name == f'group-{self.group_num}-mod':
                        mod_channel = channel

            if self.require_approval == 1:
                reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                reply += "The previous message must undergo moderator review. Reply 'yes' if the post is in violation of community guidelines, otherwise 'no'" + "\n-\n-\n"
                await mod_channel.send(reply)
                self.waiting_mod = 1
            else:
                reply = "MESSAGE_TO_MODERATOR_LOGS\n"
                reply += "The previous message does not need moderator review, and the previous pending actions will be taken." + "\n-\n-\n"
                await mod_channel.send(reply)


        except Exception as e:
                # Get the stack trace as a string
                stack_trace = traceback.format_exc()
                
                # Construct the error message with detailed information
                error_message = (
                    "Oops! Something went wrong. Here's the error message and additional details:\n\n"
                    f"Error Type: {type(e).__name__}\n"
                    f"Error Details: {str(e)}\n\n"
                    "Stack Trace:\n"
                    f"{stack_trace}"
                )
                
                # Send the detailed error message to the Discord channel
                await mod_channel.send(error_message)
                return

        


client = ModBot()
client.run(discord_token)