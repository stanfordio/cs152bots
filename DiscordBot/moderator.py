from enum import Enum, auto
import discord
import json
import re
from supabase_client import SupabaseClient

supabase = SupabaseClient()

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
        "Increase the number of times user has submitted false reports",
        "Automated report"
    ]
    REPORT_FREQUENCY_DECISION_OPTIONS = [
        "Report to law enforcement, NCMEC, and Lantern",
        "Increase the number of times this user has been reported",
    ]

    def __init__(self, client, message):
        self.client = client
        self.original_message = message
        self.state = ModeratorState.EVAL_START
        self.current_report = None
        self.reported_user_id = None
        self.reported_user_name = None
    
    async def handle_report(self, message):
        report = self.original_message
        replies = []
        
        if self.state == ModeratorState.EVAL_START:
            next_report = supabase.fetch_next_report()
            if not next_report:
                return ["There are no active reports in the queue at the moment."]
            self.current_report = next_report
            self.reported_user_id = self.current_report['reported_user']
            self.state = ModeratorState.AWAITING_VERACITY_DECISION
            return [self.format_report(next_report),
                    f"This is the highest priority report in the queue.",
                    self.create_options_list("Is this a legit report?",
                                             self.VERACITY_OPTIONS)]
        
        if self.state == ModeratorState.AWAITING_VERACITY_DECISION:
            i = self.get_index(message, self.VERACITY_OPTIONS)

            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                self.state = ModeratorState.AWAITING_LEGIT_REPORT_DECISION
                reply = self.create_options_list("This is a legit report. How would you like to proceed?",
                                                 self.LEGIT_REPORT_DECISION_OPTIONS)
                return [reply]
            elif i == 1:
                self.state = ModeratorState.AWAITING_FALSE_REPORT_DECISION
                num_false_reports = supabase.fetch_num_false_reports_submitted(self.current_report['reported_by'])
                reply = self.create_options_list(f"<@{self.current_report['reported_by']}> has submitted {num_false_reports} fake reports in the past. How would you like to proceed?",
                                                 self.FALSE_REPORT_DECISION_OPTIONS)
                return [reply]
            else:
                await self.handle_escalate_moderation(report)
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
                supabase.increment_num_false_reports_submitted(self.current_report['reported_by'])
                reply = "We increased the number of false reports associated to this user. We are closing the report."
                replies += [reply]
            
            if i == 2:
                self.state = ModeratorState.ACTION_COMPLETE
                reply = "False report issued by bot. No further action needed. We are closing the report."
                replies += [reply]
        
        if self.state == ModeratorState.AWAITING_LEGIT_REPORT_DECISION:
            i = self.get_index(message, self.LEGIT_REPORT_DECISION_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                await self.handle_escalate_law(report)
                await self.handle_ban(report)
                self.state = ModeratorState.ACTION_COMPLETE

            if i == 1:
                self.state = ModeratorState.AWAITING_REPORT_FREQUENCY_DECISION
                num_reports_received = supabase.fetch_num_reports_received(self.reported_user_id)
                reply = self.create_options_list(f"<@{self.reported_user_id}> has been reported {num_reports_received} times for violating our Child Exploitation, Abuse, and Nudity Policy in the past. How would you like to proceed?",
                                                 self.REPORT_FREQUENCY_DECISION_OPTIONS)
                return [reply]
                
        if self.state == ModeratorState.AWAITING_REPORT_FREQUENCY_DECISION:
            i = self.get_index(message, self.REPORT_FREQUENCY_DECISION_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            
            if i == 0:
                await self.handle_escalate_law(report)
                await self.handle_ban(report)
                self.state = ModeratorState.ACTION_COMPLETE

            if i == 1:
                self.state = ModeratorState.AWAITING_HIDE_CHILDREN_DECISION
                supabase.increment_num_reports_received(self.reported_user_id)
                reply = self.create_options_list("We increased the number of times this user has been reported for CSAM. Would you like to hide child profiles from this user?",
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

    def create_options_list(self, prompt, options):
        res = prompt
        for i, option in enumerate(options):
            res += f"\n\t{i + 1}\. {option}"
        return res

    def get_index(self, message, options):
        try:
            i = int(message.content.strip())
            i -= 1
        except:
            return -1
        if i not in range(len(options)):
            return -1
        return i
    
    async def handle_ban(self, message):        
        if self.current_report:
            reported_user = self.current_report['reported_user']
            reported_message = self.current_report['reported_message']
            message_link = self.current_report['message_link']
            message_channel = 'group-29'
            try:
                supabase.ban_user(reported_user)
                channel = discord.utils.get(self.client.get_all_channels(), name=message_channel)
                if channel:
                    # Notify that the user can no longer send new messages
                    await channel.send(f"User <@{reported_user}> has been banned for the following message and can no longer send any messages:\n```{reported_message}```Message Link: {message_link}\n\n" )
                    
                    await message.channel.send(f"User <@{reported_user}> has been successfully banned. The reporting user has been notified.")
                else:
                    await message.channel.send("Channel not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_hide_profile(self, message):
        if self.current_report:
            reported_user = self.current_report['reported_user']
            message_channel = 'group-29'

            try:
                channel = discord.utils.get(self.client.get_all_channels(), name=message_channel)
                if channel:
                    await channel.send(f"Profile for user <@{reported_user}> has been hidden.")
                else:
                    await message.channel.send("Channel not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_escalate_moderation(self, message):
        if self.current_report:
            reported_message = self.current_report['reported_message']
            message_link = self.current_report['message_link']

            try:
                # Notify user about escalation
                user_warning_msg = f"Your report has been escalated to the next moderation team. We will contact you if needed. Thank you for your patience. Reported message:\n```{reported_message}```Message Link: {message_link}\n\n"
                
                await message.author.send(user_warning_msg)
                
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_escalate_law(self, message):
        if self.current_report:
            reported_user = self.current_report['reported_user']
            reported_message = self.current_report['reported_message']
            message_link = self.current_report['message_link']
            message_channel = 'group-29'

            try:
                channel = discord.utils.get(self.client.get_all_channels(), name=message_channel)
                if channel:
                    await channel.send(f"Report for user <@{reported_user}> has been escalated to higher authorities.\nReported Message: ```{reported_message}```Message Link: {message_link}\n\n")

                    await message.channel.send(f"Report for user <@{reported_user}> has been successfully escalated. The reporting user has been notified.")
                else:
                    await message.channel.send("Channel not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("No current report found.")

    async def handle_resolved(self, message):
        await message.channel.send("Report has been resolved.")

    def report_complete(self):
        if self.current_report:
            supabase.close_report(self.current_report['id'])
        return self.state == ModeratorState.ACTION_COMPLETE
    
    def format_report(self, data):
        reasons = data['reasons'].split(',')
        report_message = "**Report**\n\n"
        report_message += f"**Priority:** {data['priority']}\n"
        report_message += f"**Reported By:** <@{data['reported_by']}>\n"
        report_message += f"**Reported User:** <@{data['reported_user']}>\n\n"
        report_message += f"**Reported Message:**\n```{data['reported_message']}```\n"
        report_message += f"**Message Link:** {data['message_link']}\n\n"
        report_message += "**Reason(s):**\n"
        for reason in reasons:
            report_message += f"- {reason}\n"
        return report_message