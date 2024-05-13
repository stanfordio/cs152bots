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
import queue

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


import queue

class ModBot(discord.Client):
    def __init__(self): 
        # Existing initializations
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        
        # Define queues for reports
        self.queues = {
            'explicit_content': queue.Queue(),
            'explicit_danger': queue.Queue(),
            'other': queue.Queue(),
            'other_danger': queue.Queue()
        }
        self.moderator_sessions = {}
        self.active_reports = {}

    def add_to_queue(self, report):
        if report.REASON == "Explicit Content" and report.IMMINENT_DANGER:
            self.queues['explicit_danger'].put(report)
        elif report.REASON == "Explicit Content":
            self.queues['explicit_content'].put(report)
        elif report.IMMINENT_DANGER:  # This catches other cases with imminent danger
            self.queues['other_danger'].put(report)
        else:
            self.queues['other'].put(report)

    async def process_queue(self, channel, queue_name):
        if not self.queues[queue_name].empty():
            report = self.queues[queue_name].get()
            self.active_reports[channel.id] = report  # Track the active report
            await channel.send(f"Processing report from {queue_name} queue. Author: {report.AUTHOR}\nMessage: {report.OFFENSIVE_CONTENT}\n\nPlease classify this report:\n1: CSAM, 2: Violent Acts, 3: Substance Abuse, 4: Nudity or Sexual Activity, 5: Other")
        else:
            await channel.send(f"No reports to process in the {queue_name} queue.")


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
        # Ignore messages from the bot itself to prevent loops
        if message.author == self.user:
            return

        # Handling moderator login
        # if message.content.lower() == "mod":
        #     if message.author.id not in self.moderator_sessions:
        #         self.moderator_sessions[message.author.id] = message.channel
        #         queues_list = ", ".join(self.queues.keys())
        #         await message.channel.send(f"You are now logged in as a moderator. Available queues: {queues_list}. Type the name of the queue to start processing reports.")
        #     return

        # # Handle messages from moderators who are logged in
        # if message.author.id in self.moderator_sessions:
        #     if message.content.lower() in self.queues:
        #         await self.process_queue(message.channel, message.content.lower())
        #     else:
        #         await message.channel.send("Invalid queue name. Please type a valid queue name to proceed.")
        #     return
    # Handling moderator login
        if message.content.lower() == "mod":
            if message.author.id not in self.moderator_sessions:
                self.moderator_sessions[message.author.id] = message.channel
                queues_list = []
                index = 1
                for queue_name, queue in self.queues.items():
                    queues_list.append(f"{index}: {queue_name} ({len(queue.queue)})")
                    index += 1
                queues_message = "\n".join(queues_list)
                await message.channel.send(f"You are now logged in as a moderator. Available queues:\n{queues_message}\nType the number of the queue to start processing reports.")
            return

        # Handle logout command
        if message.content.lower() == "logout" and message.author.id in self.moderator_sessions:
            del self.moderator_sessions[message.author.id]
            await message.channel.send("You have been logged out as a moderator.")
            return

        # Handle queue selection by number
        if message.author.id in self.moderator_sessions and message.content.isdigit():
            queue_index = int(message.content) - 1
            if 0 <= queue_index < len(self.queues):
                queue_name = list(self.queues.keys())[queue_index]
                await self.process_queue(message.channel, queue_name)
            else:
                await message.channel.send("Invalid queue number. Please type a valid queue number to proceed.")
            return

        # Handling responses from moderators for active reports
        if message.channel.id in self.active_reports:
            report = self.active_reports[message.channel.id]
            if message.content.isdigit() and 1 <= int(message.content) <= 5:
                classifications = {1: "CSAM", 2: "Violent Acts", 3: "Substance Abuse", 4: "Nudity or Sexual Activity", 5: "Other"}
                classification = classifications[int(message.content)]
                await message.channel.send(f"Classified as {classification}.")
                await message.channel.send("Would you like to report this to the police? (yes/no)")
            elif message.content.lower() in ["yes", "no"]:
                if "police" in self.active_reports[message.channel.id]:  # Check if this is about reporting to the police
                    if message.content.lower() == "yes":
                        await message.channel.send("The content has been reported to the police.")
                    self.active_reports[message.channel.id] = "ban"  # Next question about banning
                    await message.channel.send("Would you like to ban the user? (yes/no)")
                elif "ban" in self.active_reports[message.channel.id]:  # Check if this is about banning the user
                    if message.content.lower() == "yes":
                        await message.channel.send("The user has been banned.")
                    del self.active_reports[message.channel.id]  # Clean up after processing
                    await message.channel.send("Thank you for processing the report.")
                else:
                    await message.channel.send("Please provide a valid response.")
            return
        # if message.content.lower() == "mod":
        #     if message.author.id not in self.moderator_sessions:
        #         self.moderator_sessions[message.author.id] = message.channel
        #         queues_list = []
        #         index = 1
        #         for queue_name, queue in self.queues.items():
        #             queues_list.append(f"{index}: {queue_name} ({len(queue.queue)})")
        #             index += 1
        #         queues_message = "\n".join(queues_list)
        #         await message.channel.send(f"You are now logged in as a moderator. Available queues:\n{queues_message}\nType the number of the queue to start processing reports.")
        #         return

        # # Handle queue selection by number
        # if message.author.id in self.moderator_sessions:
        #     try:
        #         queue_index = int(message.content.strip()) - 1  # Convert to 0-based index
        #         if 0 <= queue_index < len(self.queues):
        #             queue_name = list(self.queues.keys())[queue_index]
        #             await self.process_queue(message.channel, queue_name)
        #         else:
        #             await message.channel.send("Invalid queue number. Please type a valid queue number to proceed.")
        #     except ValueError:
        #         await message.channel.send("Please enter a valid number to select a queue.")
        #     return

        # # Handling responses from moderators for active reports
        # if message.channel.id in self.active_reports:
        #     report = self.active_reports[message.channel.id]
        #     if message.content.isdigit() and 1 <= int(message.content) <= 5:
        #         classifications = {1: "CSAM", 2: "Violent Acts", 3: "Substance Abuse", 4: "Nudity or Sexual Activity", 5: "Other"}
        #         classification = classifications.get(int(message.content), "Other")
        #         await message.channel.send(f"Classified as {classification}. Does this report involve imminent danger? (yes/no)")
        #     elif message.content.lower() in ["yes", "no"]:
        #         danger_status = message.content.lower() == "yes"
        #         await message.channel.send(f"Report marked {'with' if danger_status else 'without'} imminent danger. Thank you for processing.")
        #         del self.active_reports[message.channel.id]  # Clean up after processing
        #     else:
        #         await message.channel.send("Please provide a valid response.")
        #     return

        # Handle general messages in servers and DMs
        if message.guild:
            # Check if this message is from a moderator in their designated channel
            if message.channel.id in self.moderator_sessions:
                # Already handled above
                pass
            else:
                # Handle other channel messages (not from moderators or not in the designated channels)
                await self.handle_channel_message(message)
        else:
            # Handling direct messages (DMs) for report submission or other inquiries
            await self.handle_dm(message)

    

    async def send_next_report(self, moderator):
        channel = self.moderator_sessions[moderator.id]
        for queue_name, queue in self.queues.items():
            if not queue.empty():
                report = queue.get()
                await channel.send(f"Processing next report from {queue_name}: {report}")
                return
        await channel.send("No more reports to process.")
    

    # async def process_queue(self, channel, queue_name):
    #     if not self.queues[queue_name].empty():
    #         report = self.queues[queue_name].get()
    #         self.active_reports[channel.id] = report
    #         await channel.send(f"Processing report from {report.AUTHOR}")
    #     else:
    #         await channel.send("No reports to process in this queue.")

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
            self.reports[author_id] = Report(self, self.add_to_queue)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
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