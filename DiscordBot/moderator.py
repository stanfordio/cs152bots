from enum import Enum, auto
import discord
import json
import re
from supabase import create_client, Client

with open("tokens.json", "r") as f:
    tokens = json.load(f)

supabase_url = tokens.get("SUPABASE_URL")
supabase_key = tokens.get("SUPABASE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)

class ModeratorState(Enum):
    EVAL_START = auto()
    AWAITING_VERACITY_DECISION = auto()
    AWAITING_LEGIT_REPORT_DECISION = auto()
    AWAITING_FALSE_REPORT_DECISION = auto()
    AWAITING_REPORT_FREQUENCY_DECISION = auto()
    AWAITING_HIDE_CHILDREN_DECISION = auto()
    AWAITING_BAN_DECISION = auto()
    AWAITING_DECISION = auto()
    AWAITING_ACTION = auto()
    ACTION_COMPLETE = auto()

class ModeratorReport:
    START_KEYWORD = "eval"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    YES_NO_OPTIONS = [
        "Yes",
        "No"
    ]
    VERACITY_OPTIONS = [
        "Yes",
        "No",
        "Need more information. Escalate to next moderator team"
    ]
    LEGIT_REPORT_DECISION_OPTIONS = [
        "Escalate to law enforcement",
        "It does not violate policy/the law, but not appropriate behavior (e.g., text a minor saying they are cute)"
    ]
    FALSE_REPORT_DECISION_OPTIONS = [
        "Warn user about not submitting false reports",
        "Increase the number of times user has submitted false reports"
    ]
    REPORT_FREQUENCY_DECISION_OPTIONS = [
        "Report to NCMEC",
        "Increase the number of times this user has been reported",
    ]

    def __init__(self, client, message):
        self.client = client
        self.original_message = message
        self.state = ModeratorState.EVAL_START
        self.reported_user_id = None
        self.reported_user_name = None
        self.extract_reported_user_info()

    def extract_reported_user_info(self):
        lines = self.original_message.content.split('\n')
        for line in lines:
            if line.startswith("**Reported User:**"):
                match = re.search(r'<@(\d+)>', line)
                if match:
                    self.reported_user_id = int(match.group(1))
                match = re.search(r'\((.+?)\)', line)
                if match:
                    self.reported_user_name = match.group(1)
                break
    
    async def handle_report(self, message):
        report = self.original_message
        replies = []
        
        if self.state == ModeratorState.EVAL_START:
            self.state = ModeratorState.AWAITING_VERACITY_DECISION
            # TODO queue to retrive next report
            return [f"This is the highest priority report in the queue.",
                    self.create_options_list("Is this a legit report?",
                                             self.VERACITY_OPTIONS)]
        
        if self.state == ModeratorState.AWAITING_VERACITY_DECISION:
            i = self.get_index(message, self.VERACITY_OPTIONS)
            # self.reason.append(self.INITIAL_OPTIONS[i])

            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                self.state = ModeratorState.AWAITING_LEGIT_REPORT_DECISION
                print("awaiting")
                reply = self.create_options_list("This is a legit report. How would you like to proceed?",
                                                 self.LEGIT_REPORT_DECISION_OPTIONS)
                return [reply]
            elif i == 1:
                self.state = ModeratorState.AWAITING_FALSE_REPORT_DECISION
                reply = self.create_options_list("This is the number of times the user has submitted fake reports in the past. How would you like to proceed?",
                                                 self.FALSE_REPORT_DECISION_OPTIONS)
                return [reply]
            else:
                self.state = ModeratorState.ACTION_COMPLETE
                reply = "Report escalated to next moderator team."
                replies += [reply]

        if self.state == ModeratorState.AWAITING_FALSE_REPORT_DECISION:
            i = self.get_index(message, self.FALSE_REPORT_DECISION_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                self.state = ModeratorState.ACTION_COMPLETE
                reply = "User received a warning message. We are closing the report."
                replies += [reply]

            if i == 1:
                self.state = ModeratorState.ACTION_COMPLETE
                reply = "We increased the number of false reports associated to this user. We are closing the report."
                replies += [reply]
                # TODO increase the number of times the user has submitted false reports
        
        if self.state == ModeratorState.AWAITING_LEGIT_REPORT_DECISION:
            i = self.get_index(message, self.LEGIT_REPORT_DECISION_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                await self.handle_escalate(report)
                await self.handle_ban(report)
                self.state = ModeratorState.ACTION_COMPLETE

            if i == 1:
                self.state = ModeratorState.AWAITING_REPORT_FREQUENCY_DECISION
                reply = self.create_options_list("This is the number of times the user has been reported for potential CSAM. How would you like to proceed?",
                                                 self.REPORT_FREQUENCY_DECISION_OPTIONS)
                return [reply]
                
        if self.state == ModeratorState.AWAITING_REPORT_FREQUENCY_DECISION:
            i = self.get_index(message, self.REPORT_FREQUENCY_DECISION_OPTIONS)
            print(i, "?????????")
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                await self.handle_escalate(report)
                await self.handle_ban(report)
                self.state = ModeratorState.ACTION_COMPLETE

            if i == 1:
                print(i, "*********")
                self.state = ModeratorState.AWAITING_HIDE_CHILDREN_DECISION
                # TODO increase number of times user has been reported
                reply = self.create_options_list("We increased the number of false reports associated to this user. Would you like to hide child profiles from this user?",
                                                 self.YES_NO_OPTIONS)
                return [reply]

        if self.state == ModeratorState.AWAITING_HIDE_CHILDREN_DECISION:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                await self.handle_hide_profile(report)
                self.state = ModeratorState.ACTION_COMPLETE

            if i == 1:
                self.state = ModeratorState.ACTION_COMPLETE

        if self.state == ModeratorState.ACTION_COMPLETE:
            self.report_complete()
            self.state = ModeratorState.EVAL_START
            return replies + ["Report completed."] 

    # TODO: Trigger the appropriate action based on the commands below.

    def create_options_list(self, prompt, options):
        res = prompt
        for i, option in enumerate(options):
            res += f"\n\t{i + 1}\. {option}"
        return res

    def get_index(self, message, options):
        print(message.content)
        try:
            i = int(message.content.strip())
            print(f'option: {i}')
            i -= 1
        except:
            return -1
        print(range(len(options)))
        if i not in range(len(options)):
            return -1
        return i
    
    async def handle_ban(self, message):
        current_report = supabase.table('User').select('*').eq('current_report', True).execute()

        if len(current_report.data) > 0:
            report_data = current_report.data[0]
            reported_user = report_data['reported_user']
            reported_message = report_data['reported_message']
            message_link = report_data['message_link']
            message_channel = report_data['message_channel']

            try:
                channel = discord.utils.get(self.client.get_all_channels(), name=message_channel)
                if channel:
                    await channel.send(f"User {reported_user} has been banned for the following message:\n```{reported_message}```\nMessage Link: {message_link}")

                    await message.channel.send(f"User {reported_user} has been successfully banned. The reporting user has been notified.")
                else:
                    await message.channel.send("Channel not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_hide_profile(self, message):
        current_report = supabase.table('User').select('*').eq('current_report', True).execute()

        if len(current_report.data) > 0:
            report_data = current_report.data[0]
            reported_user = report_data['reported_user']
            message_channel = report_data['message_channel']

            try:
                channel = discord.utils.get(self.client.get_all_channels(), name=message_channel)
                if channel:
                    await channel.send(f"Profile for user {reported_user} has been hidden.")
                else:
                    await message.channel.send("Channel not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_escalate(self, message):
        current_report = supabase.table('User').select('*').eq('current_report', True).execute()

        if len(current_report.data) > 0:
            report_data = current_report.data[0]
            reported_user = report_data['reported_user']
            reported_message = report_data['reported_message']
            message_link = report_data['message_link']
            message_channel = report_data['message_channel']

            try:
                channel = discord.utils.get(self.client.get_all_channels(), name=message_channel)
                if channel:
                    await channel.send(f"Report for user {reported_user} has been escalated to higher authorities.\nReported Message: ```{reported_message}```\nMessage Link: {message_link}")

                    await message.channel.send(f"Report for user {reported_user} has been successfully escalated. The reporting user has been notified.")
                else:
                    await message.channel.send("Channel not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_resolved(self, message):
        await message.channel.send("Report has been resolved.")

    def report_complete(self):
        return self.state == ModeratorState.ACTION_COMPLETE