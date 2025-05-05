# report.py
from enum import Enum, auto
import discord
import re
import asyncio
from datetime import datetime

class ReportType(Enum):
    DOXXING = "Doxxing"
    HARASSMENT = "Harassment"
    HATE_SPEECH = "Hate Speech"
    SPAM = "Spam"
    INAPPROPRIATE = "Inappropriate Content"
    OTHER = "Other"

class Severity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_REPORT_TYPE = auto()
    AWAITING_DOXXING_DETAILS = auto()
    AWAITING_SEVERITY = auto()
    AWAITING_CONFIRMATION = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    
    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_type = None
        self.details = None
        self.severity = None
        self.reporter_id = None
        self.timestamp = None
        
    async def handle_message(self, message):
        '''
        This function handles the reporting flow by managing state transitions
        and prompts at each state.
        '''
        
        if message.content.lower() == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if message.content.lower() == self.HELP_KEYWORD:
            return [self.get_help_message()]
            
        if self.state == State.REPORT_START:
            self.reporter_id = message.author.id
            self.timestamp = datetime.now()
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
            
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            try:
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            self.state = State.AWAITING_REPORT_TYPE
            
            reply = f"I found this message from {self.message.author.name}:\n"
            reply += f"```{self.message.content}```\n"
            reply += "What type of report would you like to file? Please select one of the following by typing the number:\n\n"
            reply += "1. Doxxing (sharing personal information)\n"
            reply += "2. Harassment\n"
            reply += "3. Hate Speech\n"
            reply += "4. Spam\n"
            reply += "5. Inappropriate Content\n"
            reply += "6. Other"
            
            return [reply]
        
        if self.state == State.AWAITING_REPORT_TYPE:
            try:
                selection = int(message.content.strip())
                report_types = list(ReportType)
                if 1 <= selection <= len(report_types):
                    self.report_type = report_types[selection-1]
                    
                    # For doxxing reports, collect specific details
                    if self.report_type == ReportType.DOXXING:
                        self.state = State.AWAITING_DOXXING_DETAILS
                        response = f"You selected: {self.report_type.value}\n\n"
                        response += "Please specify what personal information was shared:\n"
                        response += "(For example: real name, address, phone number, email, photos, etc.)"
                        return [response]
                    else:
                        # For other report types, jump to severity
                        self.state = State.AWAITING_SEVERITY
                        response = f"You selected: {self.report_type.value}\n\n"
                        response += "Please rate the severity of this situation:\n\n"
                        response += "1. Low - Minor concern\n"
                        response += "2. Medium - Moderate concern\n"
                        response += "3. High - Serious concern\n"
                        response += "4. Urgent - Immediate attention needed"
                        return [response]
                else:
                    return ["Please enter a valid number between 1 and 6."]
            except ValueError:
                return ["Please enter a number to select a report type."]
        
        if self.state == State.AWAITING_DOXXING_DETAILS:
            # Store the details provided by the user
            self.details = message.content
            
            self.state = State.AWAITING_SEVERITY
            response = "Thank you for the details.\n\n"
            response += "Please rate the severity of this situation:\n\n"
            response += "1. Low - Minor concern\n"
            response += "2. Medium - Moderate concern\n"
            response += "3. High - Serious concern\n"
            response += "4. Urgent - Immediate attention needed"
            return [response]
        
        if self.state == State.AWAITING_SEVERITY:
            try:
                selection = int(message.content.strip())
                severity_levels = list(Severity)
                if 1 <= selection <= len(severity_levels):
                    self.severity = severity_levels[selection-1]
                    
                    # Create a summary for confirmation
                    self.state = State.AWAITING_CONFIRMATION
                    
                    summary = "**Report Summary:**\n\n"
                    summary += f"**Type:** {self.report_type.value}\n"
                    summary += f"**Severity:** {self.severity.value}\n"
                    summary += f"**Message Author:** {self.message.author.name}\n"
                    summary += f"**Message Content:** ```{self.message.content}```\n"
                    
                    if self.details:
                        summary += f"**Additional Details:** {self.details}\n\n"
                    
                    summary += "Is this information correct? Type `yes` to submit the report or `no` to cancel."
                    
                    return [summary]
                else:
                    return ["Please enter a valid number between 1 and 4."]
            except ValueError:
                return ["Please enter a number to select a severity level."]
        
        if self.state == State.AWAITING_CONFIRMATION:
            if message.content.lower() == "yes":
                # Submit the report to moderators
                await self._submit_report_to_mods()
                
                self.state = State.REPORT_COMPLETE
                response = "Thank you for submitting your report. It has been forwarded to our moderation team.\n\n"
                response += "Our moderators will review your report as soon as possible.\n"
                response += f"The severity of your report has been marked as {self.severity.value}, which will help moderators prioritize their response.\n\n"
                response += "If you need to submit another report, type `report` again."
                return [response]
            elif message.content.lower() == "no":
                self.state = State.REPORT_COMPLETE
                return ["Report cancelled. If you need to submit a different report, type `report` again."]
            else:
                return ["Please type `yes` to confirm or `no` to cancel."]
        
        # If we somehow end up in an unknown state
        return ["An error occurred in the reporting process. Please type `report` to start again."]
    
    async def _submit_report_to_mods(self):
        """
        Send the report to the moderator channel for the guild.
        """
        if not self.message or not self.report_type:
            return
        
        # Get the mod channel for this guild
        guild_id = self.message.guild.id
        if guild_id not in self.client.mod_channels:
            return
        
        mod_channel = self.client.mod_channels[guild_id]
        
        # Create an embed for the report
        embed = discord.Embed(
            title=f"New Report: {self.report_type.value}",
            color=self._get_severity_color(),
            timestamp=self.timestamp
        )
        
        embed.add_field(name="Reported Message", value=self.message.content[:1024], inline=False)
        embed.add_field(name="Message Author", value=f"{self.message.author.name} (ID: {self.message.author.id})", inline=True)
        embed.add_field(name="Reporter", value=f"<@{self.reporter_id}>", inline=True)
        embed.add_field(name="Severity", value=self.severity.value, inline=True)
        
        if self.details:
            embed.add_field(name="Additional Details", value=self.details[:1024], inline=False)
            
        embed.add_field(name="Message Link", value=f"[Click to view]({self.message.jump_url})", inline=False)
        
        # Send the report to the mod channel
        await mod_channel.send(embed=embed)
    
    def _get_severity_color(self):
        """Return a color based on the severity level."""
        if self.severity == Severity.LOW:
            return 0x3498db  # Blue
        elif self.severity == Severity.MEDIUM:
            return 0xf1c40f  # Yellow
        elif self.severity == Severity.HIGH:
            return 0xe67e22  # Orange
        elif self.severity == Severity.URGENT:
            return 0xe74c3c  # Red
        return 0x95a5a6  # Grey (default)
    
    def get_help_message(self):
        help_msg = "**Discord Report Bot Help**\n\n"
        
        if self.state == State.REPORT_START:
            help_msg += "To start a report, type `report`.\n"
            help_msg += "To cancel the reporting process at any time, type `cancel`."
        
        elif self.state == State.AWAITING_MESSAGE:
            help_msg += "I need the link to the message you want to report.\n"
            help_msg += "To get this link, right-click on the message and select 'Copy Message Link'.\n"
            help_msg += "Then paste that link in this chat."
        
        elif self.state == State.AWAITING_REPORT_TYPE:
            help_msg += "Please select the type of report by typing the corresponding number:\n\n"
            help_msg += "1. Doxxing - Sharing someone's personal information\n"
            help_msg += "2. Harassment - Targeted negative behavior\n"
            help_msg += "3. Hate Speech - Discrimination based on identity\n"
            help_msg += "4. Spam - Excessive or irrelevant messages\n"
            help_msg += "5. Inappropriate Content - NSFW or disturbing content\n"
            help_msg += "6. Other - Any other violations"
        
        elif self.state == State.AWAITING_DOXXING_DETAILS:
            help_msg += "Please describe what personal information was shared.\n"
            help_msg += "Examples include: real names, addresses, phone numbers, emails, social media profiles, photos, etc."
        
        elif self.state == State.AWAITING_SEVERITY:
            help_msg += "Rate the severity of the situation:\n\n"
            help_msg += "1. Low - Minor concern, no immediate danger\n"
            help_msg += "2. Medium - Moderate concern, should be addressed soon\n"
            help_msg += "3. High - Serious concern, should be addressed quickly\n"
            help_msg += "4. Urgent - Immediate attention needed, potentially harmful situation"
        
        elif self.state == State.AWAITING_CONFIRMATION:
            help_msg += "Review the report summary and confirm it's correct.\n"
            help_msg += "Type `yes` to submit the report or `no` to cancel."
        
        return help_msg
    
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE