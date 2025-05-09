from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()

    SELECT_REASON = auto()
    SCAM_TYPE = auto()
    SOLICITATION_TYPE = auto()
    INVOLVES_CRYPTO = auto()
    AWAITING_ALT_REASON = auto()
    
    REPORT_COMPLETE = auto()
    APPEAL_START = auto()
    APPEAL_REASON = auto()
    APPEAL_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    APPEAL_KEYWORD = "appeal"

    report_counts = {}
    warning_status = {}  # Track which users have received warnings
    appeal_status = {}  # Track appeal status for each user
    report_id_counter = 0
    appeal_id_counter = 0
    active_reports = {}  # Store all report details by ID
    active_appeals = {}  # Store all appeal details by ID

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.appeal_reason = None
        self.report_id = None
        self.appeal_id = None
        self.report_details = {
            'reporter': None,
            'reported_user': None,
            'reason': None,
            'message_content': None,
            'message_link': None,
            'timestamp': None,
            'status': 'pending'
        }
        self.appeal_details = {
            'appealing_user': None,
            'reason': None,
            'timestamp': None,
            'status': 'pending',
            'report_count': 0
        }

        # self.selected_reason = None
        # self.selected_scam_type = None
        # self.selected_solicitation_type = None
        # self.selected_involves_crypto = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if message.content == self.APPEAL_KEYWORD:
            if message.author.name not in self.report_counts:
                return ["You have not been reported or banned. No appeal is necessary."]
            
            self.appeal_id = self.generate_appeal_id()
            self.appeal_details['appealing_user'] = message.author.name
            self.appeal_details['timestamp'] = message.created_at
            self.appeal_details['report_count'] = self.report_counts.get(message.author.name, 0)
            
            self.state = State.APPEAL_START
            return ["You have initiated the appeal process. Please provide your reason for appeal:"]
        
        if self.state == State.REPORT_START:
            self.report_id = self.generate_report_id()
            self.report_details['reporter'] = message.author.name
            self.report_details['timestamp'] = message.created_at
            reply =  "Thank you for starting the reporting process. "
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
                message = await channel.fetch_message(int(m.group(3)))
                self.message = message
                self.report_details['message_link'] = message.jump_url
                self.report_details['message_content'] = message.content
                self.report_details['reported_user'] = message.author.name
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            self.state = State.SELECT_REASON
            return [
                "I found this message:",
                f"```{self.message.author.name}: {self.message.content}```",
                "Please select the reason for reporting this user.",
                "Options: Spam, Hatespeech, Fraud/Scam, Offensive Content, Other"
            ]

        if self.state == State.SELECT_REASON:
            reason = message.content.strip().lower()
            reported_user = self.message.author.name
            self.report_details['reason'] = reason
            if reason in ["spam", "hatespeech", "offensive content"]:
                self.state = State.REPORT_COMPLETE
                # Store report details
                Report.active_reports[self.report_id] = self.report_details
                # Forward report to mod channel
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name == f'group-{self.client.group_num}-mod':
                            await channel.send(
                                f"New Report #{self.report_id}\n"
                                f"Reporter: {self.report_details['reporter']}\n"
                                f"Reported User: {reported_user}\n"
                                f"Reason: {reason}\n"
                                f"Message: {self.message.content}\n"
                                f"Message Link: {self.message.jump_url}\n"
                                f"Timestamp: {self.report_details['timestamp']}\n"
                                f"Status: {self.report_details['status']}\n"
                                f"Use 'review {self.report_id}' to review this report."
                            )
                return [f"Thanks for reporting {reported_user}. We have blocked the reported user."]
            elif reason == "fraud/scam":
                self.state = State.SCAM_TYPE
                return ["Please select a type of scam: Solicitation, Impersonation, Other"]
            elif reason == "other":
                self.state = State.AWAITING_ALT_REASON
                return ["Please specify the reason for reporting:"]
            else:
                return ["Invalid option, please select a reason for reporting from: Spam, Hatespeech, Fraud/Scam, Offensive Content, Other"]

        if self.state == State.SCAM_TYPE:
            scam_type = message.content.strip().lower()
            if scam_type == "solicitation":
                self.state = State.SOLICITATION_TYPE
                return ["Please select the type of solicitation: Job Opportunity, Investment Opportunity, Networking Event"]
            elif scam_type == "impersonation":
                reported_user = self.message.author.name
                self.state = State.REPORT_COMPLETE
                # Store report details
                Report.active_reports[self.report_id] = self.report_details
                # Forward report to mod channel
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name == f'group-{self.client.group_num}-mod':
                            await channel.send(
                                f"New Report #{self.report_id}\n"
                                f"Reporter: {self.report_details['reporter']}\n"
                                f"Reported User: {reported_user}\n"
                                f"Reason: Fraud/Scam - Impersonation\n"
                                f"Message: {self.message.content}\n"
                                f"Message Link: {self.message.jump_url}\n"
                                f"Timestamp: {self.report_details['timestamp']}\n"
                                f"Status: {self.report_details['status']}\n"
                                f"Use 'review {self.report_id}' to review this report."
                            )
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user and forwarded the report to the moderators."]
            elif scam_type == "other":
                self.state = State.AWAITING_ALT_REASON
                return ["Please specify the reason for reporting:"]
            else:
                return ["Invalid option, please select a type of scam from: Solicitation, Impersonation, Other"]

        if self.state == State.SOLICITATION_TYPE:
            solicitation_type = message.content.strip().lower()
            reported_user = self.message.author.name
            if solicitation_type in ["job opportunity", "networking event"]:
                self.state = State.REPORT_COMPLETE
                # Store report details
                Report.active_reports[self.report_id] = self.report_details
                # Forward report to mod channel
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name == f'group-{self.client.group_num}-mod':
                            await channel.send(
                                f"New Report #{self.report_id}\n"
                                f"Reporter: {self.report_details['reporter']}\n"
                                f"Reported User: {reported_user}\n"
                                f"Reason: Fraud/Scam - Solicitation - {solicitation_type}\n"
                                f"Message: {self.message.content}\n"
                                f"Message Link: {self.message.jump_url}\n"
                                f"Timestamp: {self.report_details['timestamp']}\n"
                                f"Status: {self.report_details['status']}\n"
                                f"Use 'review {self.report_id}' to review this report."
                            )
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user and forwarded the report to the moderators."]
            elif solicitation_type == "investment opportunity":
                self.state = State.INVOLVES_CRYPTO
                return ["Does this involve cryptocurrency? (Yes/No)"]
            else:
                return ["Invalid option, please select a type of solicitation from: Job opportunity, Investment opportunity, Networking event"]

        if self.state == State.INVOLVES_CRYPTO:
            response = message.content.strip().lower()
            reported_user = self.message.author.name
            if response == "yes":
                self.state = State.REPORT_COMPLETE
                # Store report details
                Report.active_reports[self.report_id] = self.report_details
                # Forward report to mod channel
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name == f'group-{self.client.group_num}-mod':
                            await channel.send(
                                f"New Report #{self.report_id}\n"
                                f"Reporter: {self.report_details['reporter']}\n"
                                f"Reported User: {reported_user}\n"
                                f"Reason: Fraud/Scam - Solicitation - Investment Opportunity (Crypto)\n"
                                f"Message: {self.message.content}\n"
                                f"Message Link: {self.message.jump_url}\n"
                                f"Timestamp: {self.report_details['timestamp']}\n"
                                f"Status: {self.report_details['status']}\n"
                                f"Use 'review {self.report_id}' to review this report."
                            )
                return [f"Thanks for notifying us. We have blocked the reported user {self.message.author.name} and forwarded the report to the moderators."]
            elif response == "no":
                self.state = State.REPORT_COMPLETE
                # Store report details
                Report.active_reports[self.report_id] = self.report_details
                # Forward report to mod channel
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name == f'group-{self.client.group_num}-mod':
                            await channel.send(
                                f"New Report #{self.report_id}\n"
                                f"Reporter: {self.report_details['reporter']}\n"
                                f"Reported User: {reported_user}\n"
                                f"Reason: Fraud/Scam - Solicitation - Investment Opportunity\n"
                                f"Message: {self.message.content}\n"
                                f"Message Link: {self.message.jump_url}\n"
                                f"Timestamp: {self.report_details['timestamp']}\n"
                                f"Status: {self.report_details['status']}\n"
                                f"Use 'review {self.report_id}' to review this report."
                            )
                return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user and forwarded the report to the moderators."]
            else:
                return ["Invalid response, please type 'Yes' or 'No'."]

        if self.state == State.AWAITING_ALT_REASON:
            reported_user = self.message.author.name
            self.state = State.REPORT_COMPLETE
            # Store report details
            Report.active_reports[self.report_id] = self.report_details
            # Forward report to mod channel
            for guild in self.client.guilds:
                for channel in guild.text_channels:
                    if channel.name == f'group-{self.client.group_num}-mod':
                        await channel.send(
                            f"New Report #{self.report_id}\n"
                            f"Reporter: {self.report_details['reporter']}\n"
                            f"Reported User: {reported_user}\n"
                            f"Reason: {message.content}\n"
                            f"Message: {self.message.content}\n"
                            f"Message Link: {self.message.jump_url}\n"
                            f"Timestamp: {self.report_details['timestamp']}\n"
                            f"Status: {self.report_details['status']}\n"
                            f"Use 'review {self.report_id}' to review this report."
                        )
            return [f"Thanks for reporting {self.message.author.name}. We have blocked the reported user."]
        
        if self.state == State.APPEAL_START:
            self.appeal_reason = message.content
            self.appeal_details['reason'] = self.appeal_reason
            self.state = State.APPEAL_COMPLETE
            
            # Store appeal details
            Report.active_appeals[self.appeal_id] = self.appeal_details
            
            # Forward appeal to mod channel
            for guild in self.client.guilds:
                for channel in guild.text_channels:
                    if channel.name == f'group-{self.client.group_num}-mod':
                        await channel.send(
                            f"New Appeal #{self.appeal_id}\n"
                            f"Appealing User: {self.appeal_details['appealing_user']}\n"
                            f"Current Report Count: {self.appeal_details['report_count']}\n"
                            f"Appeal Reason: {self.appeal_reason}\n"
                            f"Timestamp: {self.appeal_details['timestamp']}\n"
                            f"Status: {self.appeal_details['status']}\n\n"
                            f"Use 'review appeal {self.appeal_id}' to review this appeal."
                        )
            
            return ["Your appeal has been submitted and will be reviewed by a moderator. You will be notified of the decision."]
        
        # if self.state == State.MESSAGE_IDENTIFIED:
        #     return ["<insert rest of reporting flow here>"]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def generate_report_id(self):
        Report.report_id_counter += 1
        return f"R{Report.report_id_counter:04d}"

    def generate_appeal_id(self):
        Report.appeal_id_counter += 1
        return f"A{Report.appeal_id_counter:04d}"

    def update_report_info(self, username):
        previous_count = Report.report_counts.get(username, 0)
        new_count = max(previous_count + 1, 1)
        Report.report_counts[username] = new_count
        print(f"[MOD INFO] {username} now has {new_count} report(s).")

    @classmethod
    def reset(target_class):
        # Reset all counters and stored data
        target_class.report_counts.clear()  # Clears all user report counts
        target_class.warning_status.clear()  # Clears all warning statuses
        target_class.appeal_status.clear()  # Clears all appeal statuses
        target_class.active_reports.clear()  # Clears all stored reports
        target_class.active_appeals.clear()  # Clears all stored appeals
        target_class.report_id_counter = 0  # Resets report ID counter
        target_class.appeal_id_counter = 0  # Resets appeal ID counter
        
        print("[MOD INFO] Attention: all stored report data has been reset for testing purposes.")
        print("[MOD INFO] All user report counts, warnings, and bans have been cleared.")
    


    

