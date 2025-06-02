# review.py
from enum import Enum, auto
import discord
import re
import asyncio
from datetime import datetime, timedelta
from supabase_helper import insert_victim_log

class ReportType(Enum):
    FRAUD = "Fraud"
    INAPPROPRIATE_CONTENT = "Inappropriate Content"
    HARASSMENT = "Harassment"
    PRIVACY = "Privacy"

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
    # New states for review_v2
    AWAITING_THREAT_JUDGEMENT = auto()
    AWAITING_OTHER_ABUSE_JUDGEMENT = auto()
    AWAITING_DISALLOWED_INFO = auto()
    AWAITING_CONTENT_CHECK = auto()
    AWAITING_INTENTION = auto()
    CONFIRMING_REVIEW = auto()
    REVIEW_COMPLETE = auto()
    AWAITING_FAITH_INDICATOR = auto()
    AWAITING_NAME = auto()
    NAME_CONFIRMATION = auto()
    

class Review:
    PASSWORD = "AG8Q2XJa39"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "review help"
    
    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.report = None
        self.report_details = None
        self.info_types = []
        self.details = None
        self.reporter_id = None
        self.timestamp = None
        self.victim_name = None
        
        # Assessment flags set by the reviewer for building a summary
        self.threat_identified_by_reviewer = False
        self.disallowed_info_identified = False 
        self.other_pii_identified = False 

        # Flag to indicate if the original reported message should be deleted, suspended, permanently banned, and to escalate to a secondary reviewer
        self.remove = False
        self.suspend_user = False
        self.ban_user = False 

        # Stored Discord objects for performing moderation actions- these are fetched based on information in the report_details embed
        self.original_reported_message = None 
        self.original_message_author = None
        self.abuse_type = None

    async def handle_message(self, message: discord.Message):
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
            self.timestamp = datetime.now()
            reply = "Thank you for starting the reviewing process. "
            reply += "Say `review help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the report you want to review.\n"
            reply += "You can obtain this link by right-clicking the report and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
            
        if self.state == State.AWAITING_MESSAGE:
            # Parse IDs from linked report message
            m = re.search(r'/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["Invalid message link. Please use a valid Discord message link or type `cancel`."]
            
            guild_id, channel_id, message_id = map(int, m.groups())
            guild = self.client.get_guild(guild_id)
            if not guild:
                return ["Error: Bot cannot find the server for that link."]
            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                return ["Error: Mod channel not found or not a text channel."]
            
            try:
                # Fetch the report embed itself
                self.report = await channel.fetch_message(message_id)
                if not self.report.embeds or not self.report.author.id == self.client.user.id:
                    return ["Linked message isn't a valid report embed from me. Please link the correct report."]
                self.report_details = self.report.embeds[0]

                original_message_link_str, original_author_id_str = None, None
                # Extract original message data from report fields
                for field in self.report_details.fields:
                    if field.name == "**Direct Link to Reported Message**": 
                        match = re.search(r'\((.*?)\)', field.value) 
                        if match: original_message_link_str = match.group(1)
                    elif field.name == "**Author of Reported Message**": 
                        match = re.search(r'ID: `(\d+)`', field.value)
                        if match: original_author_id_str = match.group(1)
                    if field.name == "**Specific Reason Provided by Reporter**":
                        self.abuse_type = field.value
                    if field.name == "**Victim (if provided)**":
                        self.victim_name = field.value
                
                if not original_message_link_str and self.report_details.description:
                    match = re.search(r'https?://discord\.com/channels/(\d+)/(\d+)/(\d+)', self.report_details.description)
                    if match: original_message_link_str = match.group(0)
                        
                if not original_message_link_str or not original_author_id_str:
                    return ["Error: Missing original message details in report embed. Format issue?"]

                link_parts = original_message_link_str.strip("<>").split('/')
                if len(link_parts) < 3:
                    return [f"Error: Invalid original message link format in report: {original_message_link_str}"]
                
                try:
                    orig_guild_id, orig_channel_id, orig_message_id = map(int, link_parts[-3:])
                    orig_author_id = int(original_author_id_str)
                except ValueError:
                    return ["Error parsing IDs from report embed. Corrupted data?"]

                orig_guild = self.client.get_guild(orig_guild_id)
                if not orig_guild: return [f"Error: Original guild (ID: {orig_guild_id}) not found."]
                
                orig_channel = orig_guild.get_channel(orig_channel_id)
                if not orig_channel or not isinstance(orig_channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.ForumChannel)):
                     return [f"Error: Original channel (ID: {orig_channel_id}) not found/fetchable."]
                
                message_fetchable_channel : discord.abc.Messageable = orig_channel
                try:
                    # Fetch the actual user message that was reported
                    self.original_reported_message = await message_fetchable_channel.fetch_message(orig_message_id)
                except discord.NotFound: return ["Error: Original reported message not found (deleted?)."]
                except discord.Forbidden: return ["Error: Bot permission issue fetching original message (Need 'Read History')."]

                try:
                    self.original_message_author = await orig_guild.fetch_member(orig_author_id)
                except discord.NotFound:
                    try:
                        self.original_message_author = await self.client.fetch_user(orig_author_id)
                    except discord.NotFound: return ["Error: Original author not found (neither member nor user)."]
                except discord.Forbidden: return ["Error: Bot permission issue fetching author (Need 'Members Intent'?)."]

            except (discord.errors.NotFound, IndexError) as e:
                return ["Error: Could not process linked report. Deleted or invalid format?"]

            self.state = State.AWAITING_THREAT_JUDGEMENT
            
            await message.author.send(embed=self.report_details)
            reply = "The report I found is above.\n\n"
            reply += "Does this message contain a threat of violence?\n"
            reply += "1. Yes, this post contains a threat.\n"
            reply += "2. No, this post does not contain a threat."
                
            return [reply]
        
        elif self.state == State.AWAITING_THREAT_JUDGEMENT:
            if message.content == "1": 
                self.threat_identified_by_reviewer = True
                self.remove = True
                self.suspend_user = True
            elif message.content == "2": 
                self.threat_identified_by_reviewer = False
            else:
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            
            if self.abuse_type == "Doxxing":
                self.state = State.AWAITING_DISALLOWED_INFO
                reply = ("Our platform **never** allows government identification information (e.g. social security numbers) or financial information (e.g. bank account numbers, credit card numbers) to be posted.\n\n Does the post contain any of the **expressly disallowed information** listed above?\n1. Yes, it does.\n2. No, it does not.")
                return [reply]
            else:
                self.state = State.AWAITING_OTHER_ABUSE_JUDGEMENT
                reply = f"I found this report:\n"
                for field in self.report_details.fields:
                    reply += f"{field.name}: {field.value}\n"
                reply += f"This message was flagged for {self.abuse_type}. Should this message be removed on the basis of that content?\n"
                reply += f"1. Yes, this post contains {self.abuse_type}.\n"
                reply += f"2. No, this post does not contain {self.abuse_type}."
                return [reply]
            
        elif self.state == State.AWAITING_OTHER_ABUSE_JUDGEMENT:
            if message.content == "1": 
                self.remove = True
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                    self.state = State.CONFIRMING_REVIEW
                    reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                            "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                reply = ("Review assessment (no direct threat ID'd by you):\n")
                if self.remove:
                    reply += f"- {self.report_details['**Specific Reason Provided by Reporter**']} content was identified.\n"
                    reply += "- This will be logged. The post will be removed.\n"
                else: 
                    reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]
                
        
        elif self.state == State.AWAITING_DISALLOWED_INFO:
            if message.content == "1":
                self.disallowed_info_identified = True
            elif message.content == "2":
                self.disallowed_info_identified = False
            else:
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            self.state = State.AWAITING_CONTENT_CHECK
            reply = ("Does it contain **other personally identifiable information** (phone, email, location, employer)?\n1. Yes\n2. No")
            return [reply]
        
        elif self.state == State.AWAITING_CONTENT_CHECK:
            if message.content == "1":
                self.state = State.AWAITING_FAITH_INDICATOR
                response = "Was this post:\n"
                response += " - Shared by the potentially targeted individual AND exhibits **clear** good faith\n"
                response += " - Shared by someone who knows the potentially targeted individual AND exhibits **clear** good faith\n"
                response += " - Shared to publicize a business or organization\n"
                response += "1. Yes, meets at least one of the above criteria.\n"
                response += "2. No, the post does not meet any of the above criteria.\n"
                response += "If you are unsure, click on the message link to view the message in context before returning to this review."
                return [response]
            elif message.content == "2":
                self.other_pii_identified = False
            else:
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                 self.state = State.CONFIRMING_REVIEW
                 reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                          "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                 reply = ("Review assessment (no direct threat ID'd by you):\n")
                 if self.disallowed_info_identified or self.other_pii_identified:
                     reply += "- Problematic content (Disallowed Info or Other) was identified.\n"
                     reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                 else: 
                     reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                 reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                 reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]

        elif self.state == State.AWAITING_FAITH_INDICATOR:
            if message.content == "2":
                self.other_pii_identified = True

                # Insert victim log into Doxxing Supabase (if victim name provided)
                if self.victim_name:
                    self.state = State.NAME_CONFIRMATION
                    reply = f"The victim name reported is `{self.victim_name}`. Please confirm that this is the correct name.\n"
                    reply += "1. This name is **correct**.\n"
                    reply += "2. This name is **incorrect**."
                    return[reply]
                else:
                    self.state = State.AWAITING_NAME
                    reply = "There is no victim name attached to this report. Please type the full name of the person being doxxed so the incident is accurately stored in our database."
                    return [reply]
    
            elif message.content != "1":
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                 self.state = State.CONFIRMING_REVIEW
                 reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                          "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                 reply = ("Review assessment (no direct threat ID'd by you):\n")
                 if self.disallowed_info_identified or self.other_pii_identified:
                     reply += "- Problematic content (Disallowed Info or Other) was identified.\n"
                     reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                 else: 
                     reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                 reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                 reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]
        
        elif self.state == State.NAME_CONFIRMATION:
            if message.content == "2":
                self.state = State.AWAITING_NAME
                reply = "Please type the name of the person being doxxed below:"
                return[reply]
            elif message.content != "1":
                reply = f"Please type `1` if {self.victim_name} is the correct name and `2` if incorrect."
                return [reply]
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                 self.state = State.CONFIRMING_REVIEW
                 reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                          "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                 reply = ("Review assessment (no direct threat ID'd by you):\n")
                 if self.disallowed_info_identified or self.other_pii_identified:
                     reply += "- Problematic content (Disallowed Info or Other) was identified.\n"
                     reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                 else: 
                     reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                 reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                 reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]
            

        elif self.state == State.AWAITING_NAME:
            self.victim_name = message.content
            self.state = State.NAME_CONFIRMATION
            reply = f"The name now on file is `{self.victim_name}`. Is this correct?\n"
            reply += "1. Yes, this name is correct."
            reply += "2. No, I need to re-type the name."
            return[reply]
        
        elif self.state == State.CONFIRMING_REVIEW:
            if message.content == "1":
                insert_victim_log(self.victim_name, self.timestamp)
                await self._submit_report_to_mods()
                self.state = State.REVIEW_COMPLETE
                return ["Review finalized. Outcome logged to the moderator channel. Type the password to start a new review."]
            elif message.content == "2":
                self.state = State.REVIEW_COMPLETE
                return ["Review cancelled as per your request."]
            else:
                return ["Invalid input. Please type 1 to Confirm or 2 to Cancel."]
        
        return ["An error occurred. Please type `cancel` or contact an admin."]
    
    async def _execute_moderation_actions(self):
        """
        Performs automated moderation actions (message deletion, user suspension) 
        based on the flags set during the review process

        """
        actions_taken_summary_list = []
        
        if not self.original_reported_message or not self.original_message_author:
            actions_taken_summary_list.append("Critical Error: Original message/author not identified by bot.")
            return actions_taken_summary_list

        if self.threat_identified_by_reviewer:
            # Attempt to delete reported message
            if self.remove:
                try:
                    await self.original_reported_message.delete()
                    actions_taken_summary_list.append("Original message **deleted**.")
                except discord.Forbidden:
                    actions_taken_summary_list.append("Bot **failed to delete** message (Permissions error).")
                except discord.NotFound:
                    actions_taken_summary_list.append("Original message **not found** (already deleted?).")
                except discord.HTTPException as e:
                    actions_taken_summary_list.append(f"Bot **failed to delete** message (HTTP Error: {e.status}).")
            
            if self.suspend_user:
                if isinstance(self.original_message_author, discord.Member):
                    try:
                        timeout_duration = timedelta(days=1)
                        actions_taken_summary_list.append(f"User `{self.original_message_author.display_name}` **would be suspended for 1 day** (TESTING - action disabled).")
                    except discord.Forbidden:
                        actions_taken_summary_list.append(f"Bot **failed to suspend** user `{self.original_message_author.display_name}` (Permissions error).")
                    except discord.HTTPException as e:
                        actions_taken_summary_list.append(f"Bot **failed to suspend** user `{self.original_message_author.display_name}` (HTTP Error: {e.status}).")
                else:
                    actions_taken_summary_list.append(f"User `{self.original_message_author.display_name}` **could not be suspended** (not a current server member).")
        
        if not actions_taken_summary_list: 
             actions_taken_summary_list.append("No automated actions (delete/suspend) triggered (e.g., no direct threat ID'd by reviewer).")

        return actions_taken_summary_list

    async def _submit_report_to_mods(self):
        """
        Send the review to the moderator channel for the guild.
        """
        if not self.report or not self.report_details:
            return
        
        reviewer_name = "Moderator (Reviewer ID N/A)" 
        actions_performed_strings = await self._execute_moderation_actions()
        summary_lines = []
        summary_lines.append(f"**Review of Report: `{self.report_details.title}`**") 
        if self.original_reported_message and self.original_message_author:
            summary_lines.append(f"Original Msg Author: `{self.original_message_author.display_name}` (ID: `{self.original_message_author.id}`)")
            summary_lines.append(f"Original Msg Link: [Click to View]({self.original_reported_message.jump_url})")
        else:
            summary_lines.append("Warning: Original msg/author details unavailable.")

        # Reviewer's assessment
        summary_lines.append("\n**Moderator's Assessment:**")
        summary_lines.append(f"- Threat of Violence: `{'Yes' if self.threat_identified_by_reviewer else 'No'}`")
        if self.abuse_type == "Doxxing":
            summary_lines.append(f"- Disallowed Info: `{'Yes' if self.disallowed_info_identified else 'No'}`")
        summary_lines.append(f"- Other Problematic Content: `{'Yes' if self.other_pii_identified else 'No'}`")

        summary_lines.append("\n**Outcome:**")
        summary_lines.append("- Status: First-Level Review Completed.")
        summary_lines.append("\n  **Automated Bot Actions:**")
        if actions_performed_strings:
            for item in actions_performed_strings: summary_lines.append(f"    - {item}")
        else: 
            summary_lines.append("    - No automated actions logged.") 
        
        if (not self.threat_identified_by_reviewer and 
            (self.disallowed_info_identified or self.other_pii_identified)):
                 summary_lines.append("\n  Note: Other violations noted. Manual follow-up may be needed.")

        final_summary_text = "\n".join(summary_lines)
        
        embed_title = "Review Finalized"
        embed_color = discord.Color.dark_grey()
        if self.threat_identified_by_reviewer: 
            embed_title, embed_color = "Review: Actions Taken/Logged", discord.Color.green()
        elif (self.disallowed_info_identified or self.other_pii_identified): 
            embed_title, embed_color = "Review: Findings Logged", discord.Color.blue()

        guild_id = self.report.guild.id
        mod_channel = self.client.mod_channels.get(guild_id)
        if not mod_channel:
            return

        review_embed = discord.Embed(title=embed_title, description=final_summary_text, color=embed_color, timestamp=datetime.now())
        review_embed.set_footer(text=f"Review by: {reviewer_name} | Bot v2.2")
        try:
            await mod_channel.send(embed=review_embed)
        except discord.Forbidden:
            pass
        except discord.HTTPException as e:
            pass

    def get_help_message(self):
        help_msg = "**Discord Review Bot Help**\n\n"
        
        if self.state == State.REVIEW_START:
            help_msg += "To start a review, type in the moderator password.\n"
            help_msg += "To cancel the reviewing process at any time, type `cancel`."
        
        elif self.state == State.AWAITING_MESSAGE:
            help_msg += "I need the link to the report you want to review. To get this link, right-click on the report and select 'Copy Message Link', then paste that link in this chat."
            REVIEW_START = auto()

        elif self.state == State.AWAITING_THREAT_JUDGEMENT:
            help_msg += "Please identify whether the post in question contains a threat of violence. Posts labeled as a threat will be removed.\n"
            help_msg += "1. Yes, a threat is present.\n"
            help_msg += "2. No, a threat is **not** present."

        elif self.state == State.AWAITING_OTHER_ABUSE_JUDGEMENT:
            help_msg += f"The report was labeled as {self.abuse_type}. Does this content contain {self.abuse_type}?\n"
            help_msg += f"1. Yes, the post contains {self.abuse_type}.\n"
            help_msg += f"2. No, the post does **not** contain {self.abuse_type}."
        
        elif self.state == State.AWAITING_DISALLOWED_INFO:
            help_msg += "The following information is never allowed on our platform:\n"
            help_msg += " - Government ID (e.g. Social Security Numbers, ID numbers, etc.)\n"
            help_msg += " - Personal financial information (e.g. bank account numbers, credit card numbers, etc.\n"
            help_msg += "It is important to know if this post contains any of that information. Posts labeled as containing disallowed information will be removed and the users will be suspended. Does this post contain disallowed information?\n"
            help_msg += "1. Yes, this post **contains expressly disallowed information**\n"
            help_msg += "2. No, it does not.\n"
        
        elif self.state == State.AWAITING_CONTENT_CHECK:
            help_msg += "Please type `1` if the post contains other personally identifiable information, such as phone, email, location, employer. Type `2` otherwise."
        
        elif self.state == State.AWAITING_INTENTION:
            help_msg += "Any individual or business may post their own information (except for government and financial information). Otherwise, we have stricter policy guidelines.\n"
            help_msg += "Private and potentially sensitive information posted about a **business** must **lack bad faith**. Neutral posts are allowed."
            help_msg += "Private and potentially sensitive information posted about an **individual** must be shared in **good faith**. This is a higher threshold than for businesses - ambiguous posts should be removed.\n"
            help_msg += "Enter `1` if:\n"
            help_msg += " - A person is posting their own information.\n"
            help_msg += " - A businesses information is posted and there is no bad intent.\n"
            help_msg += " - An individual's information is posted and there is **good** intent.\n"
            help_msg += "Otherwise, enter `2`."

        elif self.state == State.AWAITING_NAME:
            help_msg += "Please type the name of the individual who is being doxxed."
        
        elif self.state == State.NAME_CONFIRMATION:
            help_msg += f"It is important that we have the correct victim name in our database. The victim name on file for this report is `{self.victim_name}`. Type `1` if this is the correct name and `2` if this name is incorrect."

        return help_msg
    
    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE