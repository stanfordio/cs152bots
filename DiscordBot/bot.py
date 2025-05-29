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
from google import genai
import asyncio
from datetime import datetime


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
    gemini_api_key = tokens['gemini']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        # super().__init__(command_prefix='.', intents=intents)
        super().__init__(intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.report_status = {}
        self.report_data = {}
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.batch_messages = []  # Store messages for batch processing
        self.batch_interval = 60  # seconds (1 minute for testing, change to 3600 for 1 hour)

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
        
        # Start batch processing
        self.loop.create_task(self.batch_process_messages())

    async def batch_process_messages(self):
        """Process messages in batches every interval"""
        while True:
            await asyncio.sleep(self.batch_interval)
            
            if not self.batch_messages:
                continue
            
            print(f"[BATCH] Processing {len(self.batch_messages)} messages")
            
            # Create batch text
            batch_text = "\n".join([f"{msg['user']}: {msg['content']}" for msg in self.batch_messages])
            
            # Analyze with Gemini
            prompt = f"""
            Analyze these Discord messages for scams:
            
            {batch_text}
            
            If any message contains scams, respond with: 
            "SCAM DETECTED: [username]
            MESSAGE: [the scam message]
            REASON: [brief reason why it's a scam]"
            
            If no scams, respond with: "NO SCAMS"
            """
            
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Check for scam detection
            if "SCAM DETECTED:" in response.text:
                # Send alert to mod channel
                for guild_id, mod_channel in self.mod_channels.items():
                    await mod_channel.send(f"{response.text}")
            
            # Clear batch
            self.batch_messages = []

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
            if message.channel.name == f'group-{self.group_num}':
                if message.content.strip().lower() == "reset":
                    Report.reset()
                    await message.channel.send("All stored report data has been reset.")
                    return
                await self.handle_channel_message(message)
            elif message.channel.name == f'group-{self.group_num}-mod':
                await self.handle_mod_channel(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            reply += "Use the `appeal` command if you have been reported or banned and wish to appeal the decision.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Handle appeal command
        if message.content == Report.APPEAL_KEYWORD:
            if author_id not in self.reports:
                self.reports[author_id] = Report(self)
            responses = await self.reports[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)
            if self.reports[author_id].report_complete():
                self.reports.pop(author_id)
            return

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
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        
        # Add to batch for processing
        self.batch_messages.append({
            'user': message.author.name,
            'content': message.content,
            'timestamp': datetime.now()
        })

    async def handle_mod_channel(self, message):
        content = message.content.strip().lower()
        
        # Handle appeal review command
        if content.startswith("review appeal"):
            strings = content.split()
            if len(strings) != 3:
                await message.channel.send("Moderator command: review appeal <appeal_id>")
                return
            appeal_id = strings[2].upper()  # Convert to uppercase for consistency
            if appeal_id not in Report.active_appeals:
                # List all available appeal IDs to help the moderator
                if Report.active_appeals:
                    available_appeals = "\n".join([f"- {aid}" for aid in Report.active_appeals.keys()])
                    await message.channel.send(
                        f"No appeal found with ID {appeal_id}\n"
                        f"Available appeals:\n{available_appeals}"
                    )
                else:
                    await message.channel.send(f"No appeal found with ID {appeal_id}")
                return
                
            appeal = Report.active_appeals[appeal_id]
            await message.channel.send(
                f"Reviewing Appeal #{appeal_id}\n"
                f"Appealing User: {appeal['appealing_user']}\n"
                f"Current Report Count: {appeal['report_count']}\n"
                f"Appeal Reason: {appeal['reason']}\n"
                f"Timestamp: {appeal['timestamp']}\n"
                f"Status: {appeal['status']}\n\n"
                "Select action:\n"
                "1. Accept appeal\n"
                "2. Escalate to manager\n"
                "3. Escalate to investigation team\n"
                "4. Notify law enforcement"
            )
            self.report_status[appeal_id] = 'appeal_review'
            return

        # Handle appeal action selection
        if 'appeal_review' in self.report_status.values():
            appeal_id = next(k for k, v in self.report_status.items() if v == 'appeal_review')
            if content in ['1', '2', '3', '4']:
                action = int(content)
                appeal = Report.active_appeals[appeal_id]
                appealing_user = appeal['appealing_user']
                
                if action == 1:
                    # Accept appeal
                    Report.report_counts[appealing_user] = 0
                    Report.warning_status[appealing_user] = False  # Clear warning status
                    Report.active_appeals[appeal_id]['status'] = 'accepted'
                    await message.channel.send(f"Appeal accepted for {appealing_user}. Report count reset.")
                elif action == 2:
                    # Escalate to manager
                    Report.active_appeals[appeal_id]['status'] = 'escalated_to_manager'
                    await message.channel.send(f"Appeal from {appealing_user} escalated to manager.")
                elif action == 3:
                    # Escalate to investigation team
                    Report.active_appeals[appeal_id]['status'] = 'escalated_to_investigation'
                    await message.channel.send(f"Appeal from {appealing_user} escalated to investigation team.")
                elif action == 4:
                    # Notify law enforcement
                    Report.active_appeals[appeal_id]['status'] = 'law_enforcement_notified'
                    await message.channel.send(f"Law enforcement notified about {appealing_user}'s case.")
                
                del self.report_status[appeal_id]
                return
            else:
                await message.channel.send("Invalid option. Please select 1, 2, 3, or 4.")
                return

        # Handle report review command
        if content.startswith("review"):
            strings = content.split()
            if len(strings) != 2:
                await message.channel.send("Moderator command: review <report_id>")
                return
            
            report_id = strings[1].upper()  # Convert to uppercase for consistency
            if report_id not in Report.active_reports:
                # List all available report IDs to help the moderator
                if Report.active_reports:
                    available_reports = "\n".join([f"- {rid}" for rid in Report.active_reports.keys()])
                    await message.channel.send(
                        f"No report found with ID {report_id}\n"
                        f"Available reports:\n{available_reports}"
                    )
                else:
                    await message.channel.send(f"No report found with ID {report_id}")
                return
            
            report = Report.active_reports[report_id]
            
            # Check if report has already been reviewed
            if report['status'] == 'reviewed':
                await message.channel.send(
                    f"Reviewing Report #{report_id}\n"
                    f"Reporter: {report['reporter']}\n"
                    f"Reported User: {report['reported_user']}\n"
                    f"Reason: {report['reason']}\n"
                    f"Message: {report['message_content']}\n"
                    f"Message Link: {report['message_link']}\n"
                    f"Timestamp: {report['timestamp']}\n"
                    f"Status: Reviewed"
                )
                return
            
            # Check if this is a fraud/scam report
            is_fraud_scam = report['reason'].lower().startswith('fraud/scam')
            
            if is_fraud_scam:
                # Fraud/Scam review path
                await message.channel.send(
                    f"Reviewing Report #{report_id}\n"
                    f"Reporter: {report['reporter']}\n"
                    f"Reported User: {report['reported_user']}\n"
                    f"Reason: {report['reason']}\n"
                    f"Message: {report['message_content']}\n"
                    f"Message Link: {report['message_link']}\n"
                    f"Timestamp: {report['timestamp']}\n"
                    f"Status: {report['status']}\n\n"
                    "Select likelihood of potential scam (Low/Moderate/High):"
                )
                self.report_status[report_id] = 'select_likelihood'
            else:
                # Other report types review path
                await message.channel.send(
                    f"Reviewing Report #{report_id}\n"
                    f"Reporter: {report['reporter']}\n"
                    f"Reported User: {report['reported_user']}\n"
                    f"Reason: {report['reason']}\n"
                    f"Message: {report['message_content']}\n"
                    f"Message Link: {report['message_link']}\n"
                    f"Timestamp: {report['timestamp']}\n"
                    f"Status: {report['status']}\n\n"
                    "Is this report valid? (Yes/No)"
                )
                self.report_status[report_id] = 'other_review'
            return

        # Handle likelihood selection for fraud/scam
        if 'select_likelihood' in self.report_status.values():
            report_id = next(k for k, v in self.report_status.items() if v == 'select_likelihood')
            if content in ['low', 'moderate', 'high']:
                Report.active_reports[report_id]['likelihood'] = content
                self.report_status[report_id] = 'select_severity'
                await message.channel.send("Select severity of potential scam (Low/Moderate/High):")
                return
            else:
                await message.channel.send("Invalid option, please type 'Low', 'Moderate', or 'High'.")
                return

        # Handle severity selection for fraud/scam
        if 'select_severity' in self.report_status.values():
            report_id = next(k for k, v in self.report_status.items() if v == 'select_severity')
            if content in ['low', 'moderate', 'high']:
                Report.active_reports[report_id]['severity'] = content
                likelihood = Report.active_reports[report_id]['likelihood']
                severity = content
                reported_user = Report.active_reports[report_id]['reported_user']

                # Initialize report count if not exists
                if reported_user not in Report.report_counts:
                    Report.report_counts[reported_user] = 0
                report_count = Report.report_counts[reported_user]
                
                # If BOTH likelihood AND severity are at least moderate -> Ban
                if (likelihood in ['moderate', 'high'] and severity in ['moderate', 'high']):
                    report_count += 1
                    Report.report_counts[reported_user] = report_count
                    Report.active_reports[report_id]['status'] = 'banned'
                    await message.channel.send(
                        f"{reported_user} has been banned due to high likelihood and severity of scam.\n\n"
                        "Additional action available:\n"
                        "1. Notify law enforcement\n"
                        "2. No additional action needed"
                    )
                    self.report_status[report_id] = 'scam_action'
                # If BOTH likelihood AND severity are low -> No action
                elif likelihood == 'low' and severity == 'low':
                    Report.active_reports[report_id]['status'] = 'no_action'
                    await message.channel.send(f"No action taken for {reported_user} - low likelihood and severity of scam.")
                    # Mark report as reviewed and store review timestamp
                    Report.active_reports[report_id]['status'] = 'reviewed'
                    Report.active_reports[report_id]['review_timestamp'] = message.created_at
                # If ONE is low and ONE is moderate -> Warning
                else:
                    report_count += 1
                    Report.report_counts[reported_user] = report_count
                    Report.warning_status[reported_user] = True  # Set warning status
                    Report.active_reports[report_id]['status'] = 'warned'
                    await message.channel.send(
                        f"{reported_user} has been warned due to moderate risk of scam.\n\n"
                        "Additional action available:\n"
                        "1. Notify law enforcement\n"
                        "2. No additional action needed"
                    )
                    self.report_status[report_id] = 'scam_action'
                return
            else:
                await message.channel.send("Invalid option, please type 'Low', 'Moderate', or 'High'.")
                return

        # Handle scam action selection
        if 'scam_action' in self.report_status.values():
            report_id = next(k for k, v in self.report_status.items() if v == 'scam_action')
            content = content.strip().strip("'").strip('"')  # Remove quotes and whitespace
            if content == '1':
                report = Report.active_reports[report_id]
                reported_user = report['reported_user']
                # Notify law enforcement
                Report.active_reports[report_id]['law_enforcement_notified'] = True
                await message.channel.send(
                    f"Law enforcement has been notified about {reported_user}'s case.\n"
                    f"Report ID: {report_id}\n"
                    f"Reason: {report['reason']}\n"
                    f"Message: {report['message_content']}\n"
                    f"Message Link: {report['message_link']}"
                )
                # Mark report as reviewed and store review timestamp
                Report.active_reports[report_id]['status'] = 'reviewed'
                Report.active_reports[report_id]['review_timestamp'] = message.created_at
                del self.report_status[report_id]
                return
            elif content == '2':
                # No additional action
                await message.channel.send("No additional action taken.")
                # Mark report as reviewed and store review timestamp
                Report.active_reports[report_id]['status'] = 'reviewed'
                Report.active_reports[report_id]['review_timestamp'] = message.created_at
                del self.report_status[report_id]
                return
            else:
                await message.channel.send("Invalid option. Please select 1 or 2.")
                return

        # Handle other report types review path
        if 'other_review' in self.report_status.values():
            report_id = next(k for k, v in self.report_status.items() if v == 'other_review')
            if content.lower() in ['yes', 'no']:
                report = Report.active_reports[report_id]
                reported_user = report['reported_user']
                
                if content.lower() == 'no':
                    await message.channel.send("Thank you for reviewing this report. No action will be taken.")
                    Report.active_reports[report_id]['status'] = 'reviewed'
                    Report.active_reports[report_id]['review_timestamp'] = message.created_at
                    del self.report_status[report_id]
                    return
                
                # Initialize report count if not exists
                if reported_user not in Report.report_counts:
                    Report.report_counts[reported_user] = 0
                report_count = Report.report_counts[reported_user]
                
                # Report is valid - increment count
                report_count += 1
                Report.report_counts[reported_user] = report_count
                
                # Check if user already has a warning
                has_warning = Report.warning_status.get(reported_user, False)
                
                if has_warning:
                    # User already has a warning - ban immediately
                    await message.channel.send(f"{reported_user} has been banned due to a new valid report after warning.")
                elif report_count == 1:
                    # First valid report
                    await message.channel.send(f"First valid report for {reported_user}. No action taken.")
                elif report_count == 2:
                    # Second valid report - send warning
                    Report.warning_status[reported_user] = True
                    await message.channel.send(f"Second valid report for {reported_user}. Warning has been sent.")
                
                # Mark report as reviewed and store review timestamp
                Report.active_reports[report_id]['status'] = 'reviewed'
                Report.active_reports[report_id]['review_timestamp'] = message.created_at
                del self.report_status[report_id]
                return
            else:
                await message.channel.send("Please answer with 'Yes' or 'No'.")
                return

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