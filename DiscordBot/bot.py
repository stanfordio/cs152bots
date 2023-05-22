# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests

#from DiscordBot import mod_flow
from report import Report, BotReactMessage
import pdb
from queue import PriorityQueue

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
    REVIEW_REPORT = "review report"
    USER_REPORTS = "generate "

    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.flagged_users = {}  # Map of users that have been flagged to users that have flagged them (for moderator review)
        self.reports_by_user = {}  # Map from user to list of reports by the user
        self.reports_about_user = {}  # Map from user to list of reports against them
        self.manual_check_queue = PriorityQueue() # Queue of reports to be manually reviewed prioritized by severity
        self.in_prog_reviews = {} # Map of mod-channel message ids to reports for reports currently in review


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
        #mod_channel = self.mod_channels[message.guild.id]
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_raw_reaction_add(self, payload):
        # Only look for reacts in the DMs 
        if not payload.guild_id:
            await self.handle_dm_react(payload)

        elif payload.channel_id == self.mod_channels[payload.guild_id].id:
            await self.handle_mod_react(payload)

    async def handle_dm_react(self, payload):
        author_id = payload.user_id
        message_id = payload.message_id
        responses = []
        logger.info(payload.emoji)
        logger.info(str(payload.emoji.name))

        # Only respond to reacts if they're part of a reporting flow
        if author_id not in self.reports or message_id not in self.reports[author_id].reporting_message_ids:
            logger.info("message id " + str(message_id) + " not in reports")
            return

        channel = await self.fetch_channel(payload.channel_id)
        responses = await self.reports[author_id].handle_react(payload)
        for r in responses:
            if not r:
                continue
            # If response prompts user for further action, save the message id
            if r.startswith("You reported fraud. Please react"):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.FRAUD_LEVEL
            elif r.startswith("You reported his person has asked you for money. Please react"):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.MONEY_LEVEL
            elif r.startswith("Thank you for reporting."):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.BLOCK_LEVEL
            else:
                await channel.send(r)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `done` command to complete an in progress report.\n"
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

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            # If response prompts user for further action, save the message id
            if "Please react with one or more of the following to specify a reason for this report" in r:
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.FIRST_LEVEL
            elif r.startswith("Thank you for reporting."):
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.BLOCK_LEVEL
            elif r.startswith("You selected other."):
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.OTHER_THREAD
            else:
                await message.channel.send(r)

        # If the report is canceled, remove it from our map
        if self.reports[author_id].report_canceled():
            self.reports.pop(author_id)

        # If the report is complete, remove it from our map but flag the reported user
        if self.reports[author_id].report_complete():
            #self.flagged_users[reported_user_id] = (author_id, self.reports[author_id].reported_issues)
            # TODO: do something with this information (maybe more for milesotne 3)
            completed_report = self.reports.pop(author_id)
            user_making_report = author_id
            user_being_reported = completed_report.reported_user_id

            if user_making_report not in self.reports_by_user:
                self.reports_by_user[user_making_report] = []
            self.reports_by_user[user_making_report].append(completed_report)

            if user_being_reported not in self.reports_about_user:
                self.reports_about_user[user_being_reported] = []
            self.reports_about_user[user_being_reported].append(completed_report)

            # take_post_down, response, severity = mod_flow.new_report(completed_report, user_being_reported,
            #                                               user_making_report, self.reports_by_user,
            #                                               self.reports_about_user)

            # For now add all reports to the manual check queue with severity 1
            # TODO for milestone 2: make severity high low or med depending on report type
            severity = 3
            if Report.THREAT in completed.reported_issues:
                severity =  1
            self.manual_check_queue.put((severity, completed_report))

        #for r in responses:
        #   await message.channel.send(r)

    async def handle_channel_message(self, message):
        if  message.channel.name == f'group-{self.group_num}':
            # Forward the messages from group channel to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))

        if message.channel.id == self.mod_channels[message.guild.id].id:
            # if a mod is chatting in the mod group:
            await self.handle_mod_msg(message)

    async def handle_mod_msg(self, message):
        mod_channel = self.mod_channels[message.guild.id]
        if message.content == self.REVIEW_REPORT:
            # If a moderator is asking to review the next report
            if self.manual_check_queue.empty():
                await mod_channel.send("Nothing to review")
            else:
                #TODO: Handle report.reported_msg is encoded in some way
                pri, report = self.manual_check_queue.get()
                #TODO for milestone 2: format this text prettier
                msg = "Reported user " + str(report.reported_user_id) + " for \n"
                for i in report.reported_issues:
                    msg += str(i) + "\n"
                msg += "Reported message\n" + str(report.reported_msg) + "\n"
                msg += "React with 1, 2, 3 for ban, suspend, no action"
                sent = await mod_channel.send(msg)
                self.in_prog_reviews[sent.id] = report

        # #TODO: (maybe) for milestone 2: I haven't tested this but the idea here is to generate a report
        # # of everything a user has reported in case they ask (for police purposes etc)
        # elif message.content.startswith(self.USER_REPORTS):
        #     #TODO: I have tested this zero
        #     l = message.content.split(' ')
        #     user_id = int(l[1])
        #     #TODO: format the reports_by_user, this will print python garbage
        #     await self.mod_channel.send(str(self.reports_by_user[user_id]))

    async def handle_mod_react(self, payload):
        # once a mod reacts to a manual review message, this should send the suspended/banned user a message simulating the bad
        # TODO: Also send the reporter a message with the decision/report? as in case 3 where we do nothing
        # TODO: Make this match the flowchart words wise
        msg_id = payload.message_id
        if msg_id not in self.in_prog_reviews:
            return
        
        report = self.in_prog_reviews[msg_id]
        reported_user = report.reported_user_id
        reporting_user = report.reporting_user_id
        emoji = payload.emoji

        #TODO: make these messages match flow chart and send messages to both users in each case
        if str(emoji.name) == '1️⃣':
            user = await self.fetch_user(reported_user)
            await user.send("You have been banned due to user reports")
            self.in_prog_reviews.pop(msg_id)
        elif str(emoji.name) == '2️⃣':
            user = await self.fetch_user(reported_user)
            await user.send("You have been suspended for 15 days due to user reports")
            self.in_prog_reviews.pop(msg_id)
        elif str(emoji.name) == '3️⃣':
            user = await self.fetch_user(reporting_user)
            await user.send("We have reviewed this case and will not be taking action")
            self.in_prog_reviews.pop(msg_id)
        
        
        
        

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


client = ModBot()
client.run(discord_token)
