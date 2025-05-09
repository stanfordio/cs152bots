# review.py
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

class InfoType(Enum):
    CONTACT = "Contact Information"
    LOCATION = "Location Information"
    FINANCIAL = "Financial Information"
    ID = "ID Information"
    EXPLICIT = "Explicit Content"
    OTHER = "Other"

class Severity(Enum):
    URGENT = "Urgent"

class State(Enum):
    REVIEW_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_THREAT_JUDGEMENT = auto()
    AWAITING_DISALLOWED_INFO = auto()
    AWAITING_CONTENT_CHECK = auto()
    AWAITING_INTENTION = auto()
    CONFIRMING_REVIEW = auto()
    REVIEW_COMPLETE = auto()

class Review:
    PASSWORD = "AG8Q2XJa39"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "review help"
    
    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.report = None
        self.report_details = None
        self.info_types = []  # Changed from info_type to info_types list
        self.details = None
        self.reporter_id = None
        self.timestamp = None
        self.remove = False
        self.ban_user = False
        self.second_reviewer = False
        
    async def handle_message(self, message):
        '''
        This function handles the reporting flow by managing state transitions
        and prompts at each state.
        '''
        
        if message.content.lower() == self.CANCEL_KEYWORD:
            self.state = State.REVIEW_COMPLETE
            return ["Review cancelled."]
        
        if message.content.lower() == self.HELP_KEYWORD:
            return [self.get_help_message()]
            
        if self.state == State.REVIEW_START:
            # self.reporter_id = message.author.id
            self.timestamp = datetime.now()
            reply = "Thank you for starting the reviewing process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the report you want to review.\n"
            reply += "You can obtain this link by right-clicking the report and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
            
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            print("Link received")
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
                self.report = await channel.fetch_message(int(m.group(3)))
                self.report_details = self.report.embeds[0]
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            self.state = State.AWAITING_THREAT_JUDGEMENT
            
            reply = f"I found this report:\n"
            for field in self.report_details.fields:
                reply += f"{field.name}: {field.value}\n"
            reply += "Does this message contain a threat of violence? Selecting yes will result in the post being removed.\n"
            reply += "1. Yes\n"
            reply += "2. No"
            
            return [reply]
        
        if self.state == State.AWAITING_THREAT_JUDGEMENT:
            if message.content == "1":
                self.threat = "Threat reported."
                self.remove = True
            elif message.content == "2":
                pass
            else:
                return ["Please enter a 1 for 'Yes' or a 2 for 'No'"]
            
            self.state = State.AWAITING_DISALLOWED_INFO
            reply = "Does this post contain any of the following disallowed information:\n"
            reply += "-Government ID information (e.g. Social Security Numbers, ID numbers, etc.)\n"
            reply += "-Financial information (e.g. bank account numbers, credit card numbers, etc.)\n"
            reply += "1. Yes\n"
            reply += "2. No"
            return [reply]
        
        if self.state == State.AWAITING_DISALLOWED_INFO:
            if message.content == "1":
                self.remove = True
                self.state = State.CONFIRMING_REVIEW
                reply = "Thank you. If you confirm this review, this post will be immediately removed and the user will be suspended.\n"
                reply += "Would you like to confirm this review?\n"
                reply += "1. Yes\n"
                reply += "2. No"
                return [reply]
            elif message.content == "2":
                self.state = State.AWAITING_CONTENT_CHECK
                reply = "Does this post contain any of the following:\n"
                reply += "-Phone numbers\n"
                reply += "-Email addresses\n"
                reply += "-Name of employer\n"
                reply += "-Physical location (e.g. home address, hometown, etc.)\n"
                reply += "1. Yes\n"
                reply += "2. No"
                return [reply]
            else:
                return ["Please enter a 1 for 'Yes' or a 2 for 'No'"]
        
        if self.state == State.AWAITING_CONTENT_CHECK:
            if message.content == "1":
                self.state = State.AWAITING_INTENTION
                reply = "Was this post shared in good faith by either the potentially targeted individual and/or someone who knows the potentially targeted individual?\n"
                reply += "1. Yes\n"
                reply += "2. No"
                return [reply]
            elif message.content == "2":
                self.state = State.CONFIRMING_REVIEW
                if self.remove:
                    reply = "Thank you. If you confirmt this review, this post will be removed, as you flagged it as a threat.\n"
                    reply += "Would you like to confirm this review?\n"
                    reply += "1. Yes\n"
                    reply += "2. No"
                else:
                    reply = "Thank you. If you confirm this review, no action will be taken.\n"
                    reply += "Would you like to confirm this review?\n"
                    reply += "1. Yes\n"
                    reply += "2. No"
                return [reply]
            else:
                return ["Please enter a 1 for 'Yes' or a 2 for 'No'"]
        
        if self.state == State.AWAITING_INTENTION:
            if message.content == "1":
                self.state = State.CONFIRMING_REVIEW
                if self.remove:
                    reply = "Thank you. If you confirm this review, this post will still be removed, as you flagged it as a threat."
                    reply += "Would you like to confirm this review?\n"
                    reply += "1. Yes\n"
                    reply += "2. No"
                else:
                    reply = "Thank you. If you confirm this review, no action will be taken."
                    reply += "Would you like to confirm this review?\n"
                    reply += "1. Yes\n"
                    reply += "2. No"
                return [reply]
            elif message.content == "2":
                if self.remove:  # post had been tagged as threat
                    self.state = State.EVALUATE_SEVERITY
                    reply = "Thank you. Since you flagged this post as both a threat and as a doxxing attempt, if you confirm this review, it will be passed to a second reviewer who may choose to contact law enforcement."
                    reply += "Would you like to confirm this review?\n"
                    reply += "1. Yes\n"
                    reply += "2. No"
                else: 
                    self.remove = True
                    self.state = State.CONFIRMING_REVIEW
                    reply = "Thank you. If you confirm this review, this post will be removed."
                    reply += "Would you like to confirm this review?\n"
                    reply += "1. Yes\n"
                    reply += "2. No"
                return [reply]
            else:
                return ["Please enter a 1 for 'Yes' or a 2 for 'No'"]
            
        if self.state == State.CONFIRMING_REVIEW:
            if message.content == "1":
                # Submit the report to moderators
                await self._submit_report_to_mods()
                            
                response = "The result of this review will now be sent to the moderation team for visibility. Thank you again for your work.\n\n"
                response += "If you need to review another report, type in the reviewing password again."
                self.state = State.REVIEW_COMPLETE

                return [response]
            elif message.content == "2":
                self.state = State.REVIEW_COMPLETE
                return ["Review cancelled. If you need to submit a different review, type the moderator password again."]
            else:
                return ["Please type `1` to confirm or `2` to cancel."]
                # Submit the report to moderators
        
        # If we somehow end up in an unknown state
        return ["An error occurred in the reviewing process. Please type the moderator password to start again."]
    
    async def _submit_report_to_mods(self):
        """
        Send the review to the moderator channel for the guild.
        """
        if not self.report:
            return
        
        # Get the mod channel for this guild
        guild_id = self.report.guild.id
        if guild_id not in self.client.mod_channels:
            return
        
        mod_channel = self.client.mod_channels[guild_id]

        embed = None

        if self.second_reviewer:
            embed = discord.Embed(
                title=f"Second Reviewer Needed: Doxxing, Potential Threat",
                color=0xe74c3c, # red
                timestamp=self.timestamp
            )
            embed.add_field(name="Original Message", value=self.report_details["Reported Message"])
            embed.add_field(name="Link", value=f"[Click to view]({self.report_details['Message Link']})", inline=True)

        else:
            embed = discord.Embed(
                title=f"Review Completed",
                color=0x95a5a6, # gray
                timestamp=self.timestamp
            )
            embed.add_field(name="Reviewed Report", value=self.report_details)
        
        # Send the report to the mod channel
        await mod_channel.send(embed=embed)
    
    def get_help_message(self):
        help_msg = "**Discord Report Bot Help**\n\n"
        
        if self.state == State.REVIEW_START:
            help_msg += "To start a review, type in the moderator password.\n"
            help_msg += "To cancel the reviewing process at any time, type `cancel`."
        
        elif self.state == State.AWAITING_MESSAGE:
            help_msg += "I need the link to the report you want to review.\n"
            help_msg += "To get this link, right-click on the report and select 'Copy Message Link'.\n"
            help_msg += "Then paste that link in this chat."
            REVIEW_START = auto()

        elif self.state == State.AWAITING_THREAT_JUDGEMENT:
            help_msg += "Please identify whether the post in question contains a threat of violence. Posts labeled as a threat will be removed.\n\n"
            help_msg += "1. Yes\n"
            help_msg += "2. No\n"
        
        elif self.state == State.AWAITING_DISALLOWED_INFO:
            help_msg += "Please identify whether the post in question contains information disallowed on our platform. Disallowed information includes:\n\n"
            help_msg += " - Government ID (e.g. Social Security Numbers, ID numbers, etc.)\n"
            help_msg += " - Personal financial information (e.g. bank account numbers, credit card numbers, etc.\n"
            help_msg += "Posts labeled as containing disallowed information will be removed and the users will be suspended. Does this post contain disallowed information?\n"
            help_msg += "1. Yes\n"
            help_msg += "2. No\n"
        
        elif self.state == State.AWAITING_CONTENT_CHECK:
            help_msg += "Please describe what specific information was shared.\n"
            help_msg += "Be as detailed as possible to help moderators address the issue effectively."
        
        elif self.state == State.AWAITING_INTENTION:
            help_msg += "Please provide the name of the person whose information was shared.\n"
            help_msg += "This helps moderators track and address the issue more effectively.\n"
            help_msg += "You can type 'anonymous' if you prefer not to disclose this information."
        
        elif self.state == State.AWAITING_CONFIRMATION:
            help_msg += "Confirm that the actions that will/will not be taken are correct.\n"
            help_msg += "Type `1` to submit the review or `2` to cancel."
        
        return help_msg
    
    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE