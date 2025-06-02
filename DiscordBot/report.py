# report.py
from enum import Enum, auto
import discord
import re
import asyncio
from datetime import datetime
from count import increment_harassment_count
from supabase_helper import victim_score 

class ReportType(Enum):
    FRAUD = "Fraud"
    INAPPROPRIATE_CONTENT = "Inappropriate Content"
    HARASSMENT = "Harassment"
    PRIVACY = "Privacy Violation"

class InfoType(Enum):
    CONTACT = "Contact Information"
    LOCATION = "Location Information"
    FINANCIAL = "Financial Information"
    ID = "ID Information"
    EXPLICIT = "Explicit Content"

class Severity(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_REPORT_TYPE = auto()
    AWAITING_FRAUD_DETAILS = auto()
    AWAITING_INAPPROPRIATE_CONTENT_DETAILS = auto()
    AWAITING_HARASSMENT_DETAILS = auto()
    AWAITING_PRIVACY_DETAILS = auto()
    AWAITING_THREAT = auto()
    AWAITING_INFO_TYPE = auto()
    AWAITING_VICTIM_NAME = auto()
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
        self.report_sub_type = None
        self.info_types = []
        self.threat = False
        self.reporter_email = None
        self.severity = 0
        self.reporter_id = None
        self.timestamp = None
        self.victim_name = None
        self.doxxing_score = None
        
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
            
        # State: REPORT_START - Initial state when 'report' is typed
        if self.state == State.REPORT_START:
            self.reporter_id = message.author.id
            self.timestamp = datetime.now()
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
            
        # State: AWAITING_MESSAGE - Expecting a Discord message link
        elif self.state == State.AWAITING_MESSAGE:
            m = re.search(r'/(\d+)/(\d+)/(\d+)', message.content)
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
            reply += "1. Fraud\n"
            reply += "2. Inappropriate Content\n"
            reply += "3. Harrasment\n"
            reply += "4. Privacy Violation\n"
            return [reply]
        
        # State: AWAITING_REPORT_TYPE - User chooses a main report category
        elif self.state == State.AWAITING_REPORT_TYPE:
            try:
                selection = int(message.content.strip())
                report_types_enum_list = list(ReportType) # Gets [ReportType.FRAUD, ReportType.INAPPROPRIATE_CONTENT, ...]
                if 1 <= selection <= len(report_types_enum_list):
                    self.report_type = report_types_enum_list[selection-1]
                    if self.report_type == ReportType.FRAUD:
                        self.state = State.AWAITING_FRAUD_DETAILS
                        response = f"You selected: {self.report_type.value}\n\n"
                        response += "Please select your reason for reporting Fraud:\n\n"
                        response += "1. Scam\n2. Misleading Content\n3. Phishing\n"
                        return [response]
                    elif self.report_type == ReportType.INAPPROPRIATE_CONTENT:
                        self.state = State.AWAITING_INAPPROPRIATE_CONTENT_DETAILS
                        response = f"You selected: {self.report_type.value}\n\n"
                        response += "Please select your reason for reporting Inappropriate Content:\n\n"
                        response += "1. Suicidal Intention/Self-Harm\n2. Graphic Violence\n3. Terrorism\n"
                        return [response]
                    elif self.report_type == ReportType.HARASSMENT:
                        self.state = State.AWAITING_HARASSMENT_DETAILS
                        response = f"You selected: {self.report_type.value}\n\n"
                        response += "Please select your reason for reporting Harassment:\n\n"
                        response += "1. Credible Threat of Violence\n2. Bullying\n3. Hate Speech\n"
                        return [response]
                    elif self.report_type == ReportType.PRIVACY:
                        self.state = State.AWAITING_PRIVACY_DETAILS
                        response = f"You selected: {self.report_type.value}\n\n"
                        response += "Please select your reason for reporting Privacy Violation:\n\n"
                        response += "1. Hacking\n2. Identity Impersonation\n3. Doxxing\n"
                        return [response]
                else:
                    # User entered a number out of range for main report types
                    return [f"Please enter a valid number between 1 and {len(report_types_enum_list)} for the report type."]
            except ValueError:
                # User did not enter a number for main report type selection
                return ["Please enter a number to select a report type."]
        # State: AWAITING_FRAUD_DETAILS - User selects a specific fraud reason
        elif self.state == State.AWAITING_FRAUD_DETAILS:
            try:
                selection = int(message.content.strip())
                fraud_reasons_map = {
                    1: ("Scam", Severity.HIGH.value),
                    2: ("Misleading Content", Severity.MEDIUM.value),
                    3: ("Phishing", Severity.URGENT.value)
                }
                if selection in fraud_reasons_map:
                    self.report_sub_type, self.severity = fraud_reasons_map[selection]
                    self.state = State.AWAITING_VICTIM_NAME
                    response = f"You selected Fraud Reason: {self.report_sub_type}.\n\n"
                    response += "(Optional) If there is a specific victim, please type their name now or type `skip` to continue."
                    return [response]
                else:
                    return [f"Please enter a valid number between 1 and {len(fraud_reasons_map)} for the fraud reason."]
            except ValueError:
                return ["Please enter a number to select the fraud reason."]
        
        # State: AWAITING_INAPPROPRIATE_CONTENT_DETAILS - User selects reason for inappropriate content
        elif self.state == State.AWAITING_INAPPROPRIATE_CONTENT_DETAILS:
            try:
                selection = int(message.content.strip())
                ic_reasons_map = {
                    1: ("Suicidal Intention/Self-Harm", Severity.URGENT.value),
                    2: ("Graphic Violence", Severity.HIGH.value),
                    3: ("Terrorism", Severity.URGENT.value)
                }
                if selection in ic_reasons_map:
                    self.report_sub_type, self.severity = ic_reasons_map[selection]
                    self.state = State.AWAITING_VICTIM_NAME
                    response = f"You selected Inappropriate Content Reason: {self.report_sub_type}.\n\n"
                    response += "(Optional) If there is a specific victim, please type their name now or type `skip` to continue."
                    return [response]
                else:
                    return [f"Please enter a valid number between 1 and {len(ic_reasons_map)} for the inappropriate content reason."]
            except ValueError:
                return ["Please enter a number for the reason."]

        # State: AWAITING_HARASSMENT_DETAILS - User selects a specific harassment reason
        elif self.state == State.AWAITING_HARASSMENT_DETAILS:
            try:
                selection = int(message.content.strip())
                harassment_reasons_map = {
                    1: ("Credible Threat of Violence", Severity.URGENT.value),
                    2: ("Bullying", Severity.MEDIUM.value),
                    3: ("Hate Speech", Severity.HIGH.value)
                }
                if selection in harassment_reasons_map:
                    self.report_sub_type, self.severity = harassment_reasons_map[selection]
                    if self.report_sub_type == "Credible Threat of Violence":
                        self.threat = True
                        print("Report Log: Credible Threat of Violence identified, self.threat=True, severity=URGENT.")
                    
                    self.state = State.AWAITING_VICTIM_NAME
                    response = f"You selected Harassment Reason: {self.report_sub_type}.\n\n"
                    response += "(Optional) If there is a specific victim, please type their name now or type `skip` to continue."
                    return [response]
                else:
                    return [f"Please enter a valid number between 1 and {len(harassment_reasons_map)} for the harassment reason."]
            except ValueError:
                return ["Please enter a number for the reason."]

        # State: AWAITING_PRIVACY_DETAILS - User selects a specific privacy violation reason.
        elif self.state == State.AWAITING_PRIVACY_DETAILS:
            try:
                selection = int(message.content.strip())
                privacy_reasons_map = {
                    1: ("Hacking", Severity.HIGH.value),
                    2: ("Identity Impersonation", Severity.MEDIUM.value),
                    3: ("Doxxing", Severity.HIGH.value) 
                }
                if selection in privacy_reasons_map:
                    self.report_sub_type, self.severity = privacy_reasons_map[selection]
                    
                    if self.report_sub_type == "Doxxing":
                        self.state = State.AWAITING_THREAT
                        response = "Does this message contain a threat of violence?\n"
                        response += "1. Yes\n2. No"
                        return [response]
                    else: 
                        self.state = State.AWAITING_VICTIM_NAME
                        response = f"You selected Privacy Reason: {self.report_sub_type}.\n\n"
                        response += "(Optional) If there is a specific victim, please type their name now or type `skip` to continue."
                        return [response]
                else:
                    return [f"Please enter a valid number between 1 and {len(privacy_reasons_map)} for the privacy reason."]
            except ValueError:
                return ["Please enter a number for the reason."]
        elif self.state == State.AWAITING_THREAT:
            if message.content == "1":
                self.threat = True
            elif message.content != "2":
                response = "Please enter 1 for 'yes' or 2 for 'no'."
                return [response]

            self.state = State.AWAITING_INFO_TYPE
            response = f"You selected Privacy Reason: Doxxing.\n\n"
            response += "What type(s) of confidential information was shared? Please select one or more of the following by typing the number(s), separated by commas (e.g., 1,3,5):\n\n"
            response += "1. Contact Information\n"
            response += "2. Location Information\n"
            response += "3. Financial Information\n"
            response += "4. ID Information\n"
            response += "5. Explicit Content\n"
            return [response]
        # State: AWAITING_INFO_TYPE - User specifies types of doxxed info- this state is reached only if Doxxing was selected under Privacy
        elif self.state == State.AWAITING_INFO_TYPE:
            try:
                selections_str = message.content.split(',')
                user_selections = [int(s.strip()) for s in selections_str]
                
                available_info_types = list(InfoType)
                valid_info_objects = []
                invalid_selection_numbers = []

                for sel_num in user_selections:
                    if 1 <= sel_num <= len(available_info_types):
                        valid_info_objects.append(available_info_types[sel_num - 1])
                    else:
                        invalid_selection_numbers.append(str(sel_num))
                
                if invalid_selection_numbers:
                    return [f"Invalid selection(s): {', '.join(invalid_selection_numbers)}. Please select numbers from the list provided, separated by commas."]

                if not valid_info_objects:
                    return ["You must select at least one type of information. Please try again, or type `cancel`."]

                self.info_types = valid_info_objects
                self.state = State.AWAITING_VICTIM_NAME

                # state will move to victim name collection next
                response = f"You specified the following information types for Doxxing: {', '.join([it.value for it in self.info_types])}.\n\n"
                response += "(Optional) If there is a specific victim, please type their name now or type `skip` to continue."
                return [response]
            except ValueError:
                return ["Invalid input. Please enter numbers separated by commas (e.g., 1,2,3). Example: 1,3"]
        
        # State: AWAITING_VICTIM_NAME - Optional victim name
        elif self.state == State.AWAITING_VICTIM_NAME:
            if message.content.lower() == "skip":
                self.victim_name = None
            else:
                self.victim_name = message.content.strip()
                self.doxxing_score = victim_score(self.victim_name)

            self.state = State.AWAITING_CONFIRMATION
            
            summary = "**Report Summary:**\n\n"
            summary += f"**Main Report Type:** {self.report_type.value}\n"
            if self.report_sub_type:
                summary += f"**Specific Reason:** {self.report_sub_type}\n"
            
            # If a victim name was provided
            if self.victim_name:
                summary += f"**Victim Name (if provided):** {self.victim_name}\n"

            # If Doxxing info types were collected, list them
            if self.info_types: 
                info_types_str = ", ".join([it.value for it in self.info_types])
                summary += f"**Types of Doxxing Info Shared:** {info_types_str}\n"

            if self.threat: 
                summary += "**Sub-Reason Implies Threat:** Yes (Credible Threat of Violence selected)\n"
            
            summary += f"\n**Reported Message Author:** {self.message.author.name}\n"
            summary += f"**Reported Message Content:** ```{self.message.content}```\n"
            summary += "Is this information correct? Type `yes` to submit the report or `no` to cancel. Please note that if you type `yes`, your account will be associated with this report."
            return [summary]
        
        # State: AWAITING_CONFIRMATION - User confirms the report details
        elif self.state == State.AWAITING_CONFIRMATION:
            if message.content.lower() == "yes":
                await self._submit_report_to_mods()
                self.state = State.REPORT_COMPLETE
                response = "Thank you for submitting your report. It has been forwarded to our moderation team.\n\n"
                response += "Our moderators will review your report as soon as possible.\n"
                response += "If you need to submit another report, type `report` again."
                return [response]
            elif message.content.lower() == "no":
                self.state = State.REPORT_COMPLETE
                return ["Report cancelled. If you need to submit a different report, type `report` again."]
            else:
                return ["Please type `yes` to confirm or `no` to cancel."]
        
        # Fallback for any unknown or unhandled state
        print(f"Report Log Error: Reached unhandled state: {self.state.name} with message content: {message.content}")
        return ["An error occurred in the reporting process. Please type `report` to start again, or `cancel` to abandon the current report."]
    
    async def _submit_report_to_mods(self):
        """
        Send the report to the moderator channel for the guild.
        """
        if not self.message or not self.report_type:
            print("Report Log Error: _submit_report_to_mods called without self.message or self.report_type.")
            return
        
        guild_id = self.message.guild.id
        mod_channel = self.client.mod_channels.get(guild_id)

        if not mod_channel:
            print(f"Report Log Error: Mod channel for guild {guild_id} not found. Cannot send report.")
            return
        
        embed_color = self._get_severity_color()

        embed = discord.Embed(
            title=f"New User Report: {self.report_type.value}", # Main Type
            color=embed_color, 
            timestamp=self.timestamp # Timestamp of when the report was initiated
        )
        
        embed.add_field(name="**Content of Reported Message**", value=f"```{self.message.content[:1000]}```" + ("... (truncated)" if len(self.message.content) > 1000 else ""), inline=False)
        embed.add_field(name="**Author of Reported Message**", value=f"{self.message.author.mention} (`{self.message.author.name}`, ID: `{self.message.author.id}`)", inline=True)
        embed.add_field(name="**Filed By (Reporter)**", value=f"<@{self.reporter_id}>", inline=True)

        if self.report_sub_type:
            embed.add_field(name="**Specific Reason Provided by Reporter**", value=self.report_sub_type, inline=False)
        
        # Victim name if provided
        if self.victim_name:
            embed.add_field(name="**Victim (if provided)**", value=self.victim_name, inline=False)

        # If Doxxing info types were collected, add them to the embed
        if self.info_types:
            info_types_display_str = "\n".join([f"- {it.value}" for it in self.info_types])
            embed.add_field(name="**Doxxing Information Types Reported**", value=info_types_display_str, inline=False)
            
        if self.threat: 
            embed.add_field(name="**Threat Assessment (by Reporter)**", value="Yes (Reporter indicated 'Credible Threat of Violence' or similar sub-reason)", inline=False)
        else:
            embed.add_field(name="**Threat Assessment (by Reporter)**", value="No (Reporter's sub-reason did not indicate a direct credible threat)", inline=False)
            
        embed.add_field(name="**Direct Link to Reported Message**", value=f"[Click to View Message]({self.message.jump_url})", inline=False)
        
        embed.set_footer(text=f"Report ID (Timestamp): {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Increment harassment count if this report is of type HARASSMENT
        if self.report_type == ReportType.HARASSMENT:
            offender_id = self.message.author.id
            increment_harassment_count(guild_id, offender_id)

        try:
            await mod_channel.send(embed=embed)
            print(f"Report Log: Successfully sent report embed to mod channel '{mod_channel.name}' in guild '{mod_channel.guild.name}'.")
        except discord.Forbidden:
            print(f"Report Log Error: Failed to send report to '{mod_channel.name}' (Forbidden - check bot permissions).")
        except discord.HTTPException as e:
            print(f"Report Log Error: Failed to send report to '{mod_channel.name}' (HTTP Error: {e.status} - {e.text}).")
    
    def _get_severity_color(self):
        """Return a color based on the self.severity level (which is an int)."""
        if self.severity == Severity.LOW.value:
            return 0x3498db  # Blue
        elif self.severity == Severity.MEDIUM.value:
            return 0xf1c40f  # Yellow
        elif self.severity == Severity.HIGH.value:
            return 0xe67e22  # Orange
        elif self.severity == Severity.URGENT.value:
            return 0xe74c3c  # Red
        return 0x95a5a6  # Grey (default/unknown)
    
    def get_help_message(self):
        help_msg = "**Discord Report Bot Help**\n\n"
        help_msg += "You can type `cancel` at any point to stop the current report process.\n\n"
        
        if self.state == State.REPORT_START:
            help_msg += "To start a new report, type `report`.\n"
        
        elif self.state == State.AWAITING_MESSAGE:
            help_msg += "I need the link to the message you want to report.\n"
            help_msg += "To get this link, right-click on the Discord message and select 'Copy Message Link'.\n"
            help_msg += "Then paste that link into this DM chat with me."
        
        elif self.state == State.AWAITING_REPORT_TYPE:
            help_msg += "Please select the main type of violation by typing the corresponding number:\n\n"
            help_msg += "1. Fraud (Scams, Misleading Content, Phishing)\n"
            help_msg += "2. Inappropriate Content (Self-Harm, Graphic Violence, Terrorism)\n"
            help_msg += "3. Harassment (Credible Threats, Bullying, Hate Speech)\n"
            help_msg += "4. Privacy (Hacking, Impersonation, Doxxing)"
        # Help for the new sub-reason states
        elif self.state == State.AWAITING_FRAUD_DETAILS:
            help_msg += "You are reporting Fraud. Please select the specific reason by typing the number:\n\n"
            help_msg += "1. Scam\n"
            help_msg += "2. Misleading Content\n"
            help_msg += "3. Phishing"
        elif self.state == State.AWAITING_INAPPROPRIATE_CONTENT_DETAILS:
            help_msg += "You are reporting Inappropriate Content. Please select the specific reason by typing the number:\n\n"
            help_msg += "1. Suicidal Intention/Self-Harm\n"
            help_msg += "2. Graphic Violence\n"
            help_msg += "3. Terrorism"
        elif self.state == State.AWAITING_HARASSMENT_DETAILS:
            help_msg += "You are reporting Harassment. Please select the specific reason by typing the number:\n\n"
            help_msg += "1. Credible Threat of Violence\n"
            help_msg += "2. Bullying\n"
            help_msg += "3. Hate Speech"
        elif self.state == State.AWAITING_PRIVACY_DETAILS:
            help_msg += "You are reporting a Privacy violation. Please select the specific reason by typing the number:\n\n"
            help_msg += "1. Hacking\n"
            help_msg += "2. Identity Impersonation\n"
            help_msg += "3. Doxxing (will ask for more details)"

        elif self.state == State.AWAITING_THREAT:
            help_msg += "Please indicate if the message you would like to report contains a threat of violence:\n\n"
            help_msg += "1. Yes\n"
            help_msg += "2. No"
        
        elif self.state == State.AWAITING_INFO_TYPE:
            help_msg += "You are reporting Doxxing. Please specify the type(s) of confidential information shared.\n"
            help_msg += "Select one or more numbers from the list, separated by commas (e.g., 1,3 or 2,4,5).\n\n"
            help_msg += "1. Contact Information\n"
            help_msg += "2. Location Information\n"
            help_msg += "3. Financial Information\n"
            help_msg += "4. ID Information\n"
            help_msg += "5. Explicit Content\n"
            help_msg += "\nType `cancel` to cancel the report."

        elif self.state == State.AWAITING_VICTIM_NAME:
            help_msg += "Please provide the name of the victim if known, or type `skip` if not provided."
        
        elif self.state == State.AWAITING_CONFIRMATION:
            help_msg += "Please review the report summary I provided.\n"
            help_msg += "Type `yes` to submit the report with these details, or `no` to cancel the report."
        
        else: # Default help or for states with no specific help yet
            help_msg += "If you are unsure how to proceed, you can type `cancel` to start over, or ask a moderator for assistance if the bot seems stuck."
            
        return help_msg
    
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE