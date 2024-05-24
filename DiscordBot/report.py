from enum import Enum, auto
import re
from datetime import datetime
import discord
import logging
import sqlite3

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

LOWER_PRIORITY = 2
HIGHER_PRIORITY = 1


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    BLOCK_USER = auto()
    REPORT_COMPLETE = auto()
    BLOCK_START = auto()
    AWAITING_BLOCK = auto()
    AWAITING_BLOCK_CONFIRM = auto()
    BLOCK_COMPLETE = auto()
    PROMPTING_ADDITIONAL_DETAILS = auto()
    AWAITING_DETAILS = auto()

    # Abuse Types
    SPAM = auto()
    HARM_ENDANGERMENT = auto()
    SEXUALLY_EXPLICIT = auto()
    FRAUD = auto()
    FINANCIAL_FRAUD_CLASSIFICATION = auto()
    MISINFORMATION = auto()
    HATE_HARASSMENT = auto()
    CSAM = auto()
    INTELLECTUAL = auto()
    ILLICIT_TRADE_SUBSTANCES = auto()

    # Abuse Subcategories
    DRUGS = auto()
    COUNTERFEIT_GOODS = auto()
    BLACK_MARKET = auto()
    COPYRIGHT = auto()
    TRADEMARK = auto()
    SELF_HARM = auto()
    TERRORISM = auto()
    VIOLENCE_ABUSE = auto()
    DEATH_SEVERE_INJURY = auto()
    NUDITY_PORNOGRAPHY = auto()
    SEXUAL_HARASSMENT_OR_ABUSE = auto()
    IMPERSONATION = auto()
    ROMANCE = auto()
    HEALTH = auto()
    CRYPTOCURRENCY = auto()
    INVESTMENT = auto()
    PHISHING = auto()
    CREDIT_CARD = auto()
    CLIMATE = auto()
    POLITICAL = auto()
    BULLYING = auto()
    DOXXING = auto()
    HATE_SPEECH = auto()
    STALKING = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    BLOCK_KEYWORD = "block"
    REPORTING_OPTIONS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

    def __init__(self, client=None, report_id=None, reported_user_id=None, reporter_user_id=None,
                 reportee=None, reported_user=None, reported_message=None, report_category=None,
                 report_subcategory=None, additional_details=None, priority=None, report_status=None,
                 time_reported=None):
        self.client = client
        self.report_id = report_id
        self.reported_user_id = reported_user_id
        self.reporter_user_id = reporter_user_id
        self.reportee = reportee
        self.reported_user = reported_user
        self.reported_message = reported_message
        self.report_category = report_category
        self.report_subcategory = report_subcategory
        self.additional_details = additional_details
        self.priority = priority
        self.report_status = report_status
        self.time_reported = time_reported if time_reported else datetime.now()

    def __lt__(self, other):
        return self.priority < other.priority and self.time_reported < other.time_reported

    async def handle_message(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Process cancelled."]

        if message.content.startswith(self.BLOCK_KEYWORD):
            return await self.handle_block(message)

        if message.content.startswith(self.START_KEYWORD):
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.time_reported = datetime.now()
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
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
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            self.state = State.MESSAGE_IDENTIFIED
            self.reported_user = message.author.name
            self.reported_message = message
            reply = "I found this message:" + "```" + \
                message.author.name + ": " + message.content + "```" + "\n\n"
            reply += "Why are you reporting this message? Please select the number corresponding to the appropriate category.\n"
            reply += "1. Spam.\n"
            reply += "2. Harm and endangerment.\n"
            reply += "3. Nudity and sexual content.\n"
            reply += "4. Fraud or scam.\n"
            reply += "5. Misinformation.\n"
            reply += "6. Hate and harassment.\n"
            reply += "7. Sexual content involving a child.\n"
            reply += "8. Intellectual property theft.\n"
            reply += "9. Illicit trade and substances.\n"
            return [reply]

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content not in self.REPORTING_OPTIONS:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            return self.classify_report(message)

        if self.state == State.HARM_ENDANGERMENT:
            if message.content not in ["1", "2", "3", "4"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.SELF_HARM
            elif message.content == "2":
                self.report_subcategory = State.TERRORISM
            elif message.content == "3":
                self.report_subcategory = State.VIOLENCE_ABUSE
            else:
                self.report_subcategory = State.DEATH_SEVERE_INJURY

            return self.complete_report()

        if self.state == State.SEXUALLY_EXPLICIT:
            if message.content not in ["1", "2"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.NUDITY_PORNOGRAPHY
                self.priority = LOWER_PRIORITY
            else:
                self.report_subcategory = State.SEXUAL_HARASSMENT_OR_ABUSE
                self.priority = HIGHER_PRIORITY

            return self.complete_report()

        if self.state == State.FRAUD:
            if message.content not in ["1", "2", "3"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.IMPERSONATION
            elif message.content == "2":
                self.report_subcategory = State.ROMANCE
            else:
                self.state = State.FINANCIAL_FRAUD_CLASSIFICATION
                reply = "What kind of financial fraud are you reporting?\n"
                reply += "1. Cryptocurrency.\n"
                reply += "2. Investment.\n"
                reply += "3. Phishing.\n"
                reply += "4. Credit card fraud.\n"
                return [reply]

            return self.complete_report()

        if self.state == State.FINANCIAL_FRAUD_CLASSIFICATION:
            if message.content not in ["1", "2", "3", "4"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.CRYPTOCURRENCY
            elif message.content == "2":
                self.report_subcategory = State.INVESTMENT
            elif message.content == "3":
                self.report_subcategory = State.PHISHING
            else:
                self.report_subcategory = State.CREDIT_CARD

            self.state = State.PROMPTING_ADDITIONAL_DETAILS
            reply = "We may investigate your private message history when evaluating this report. Would you like to include any additional details? Please respond with `yes` or `no`."
            return [reply]

        if self.state == State.MISINFORMATION:
            if message.content not in ["1", "2", "3"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.HEALTH
            elif message.content == "2":
                self.report_subcategory = State.CLIMATE
            else:
                self.report_subcategory = State.POLITICAL

            return self.complete_report()

        if self.state == State.HATE_HARASSMENT:
            if message.content not in ["1", "2", "3", "4"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.BULLYING
            elif message.content == "2":
                self.report_subcategory = State.DOXXING
            elif message.content == "3":
                self.report_subcategory = State.HATE_SPEECH
            else:
                self.report_subcategory = State.STALKING

            return self.complete_report()

        if self.state == State.INTELLECTUAL:
            if message.content not in ["1", "2"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.COPYRIGHT
            else:
                self.report_subcategory = State.TRADEMARK

            return self.complete_report()

        if self.state == State.ILLICIT_TRADE_SUBSTANCES:
            if message.content not in ["1", "2", "3"]:
                return ["That is not a valid option. Please select the number corresponding to the appropriate category for reporting this message, or say `cancel` to cancel."]

            if message.content == "1":
                self.report_subcategory = State.DRUGS
            elif message.content == "2":
                self.report_subcategory = State.COUNTERFEIT_GOODS
            else:
                self.report_subcategory = State.BLACK_MARKET

            return self.complete_report()

        if self.state == State.PROMPTING_ADDITIONAL_DETAILS:
            if message.content != "yes" and message.content != "no":
                return ["That is not a valid option. Please reply with `yes` or `no`."]

            self.state = State.AWAITING_DETAILS
            if message.content == "yes":
                return ["Please provide any additional details below."]
            elif message.content == "no":
                return self.complete_report()

        if self.state == State.AWAITING_DETAILS:
            self.additional_details = message.content
            return self.complete_report()

        if self.state == State.BLOCK_USER:
            if message.content != "yes" and message.content != "no":
                return ["That is not a valid option. Please reply with `yes` or `no`."]

            self.state = State.REPORT_COMPLETE
            if message.content == "yes":
                return ["Thank you. The user has been blocked."]
            else:
                return ["Thank you. The user has not been blocked."]

        return []

    def classify_report(self, message):
        if message.content == "1":
            self.report_category = State.SPAM
            self.priority = LOWER_PRIORITY
            return self.complete_report()
        elif message.content == "2":
            self.state = State.HARM_ENDANGERMENT
            self.report_category = State.HARM_ENDANGERMENT
            self.priority = HIGHER_PRIORITY
            return self.classify_offensive_content()
        elif message.content == "3":
            self.state = State.SEXUALLY_EXPLICIT
            self.report_category = State.SEXUALLY_EXPLICIT
            return self.classify_nudity()
        elif message.content == "4":
            self.state = State.FRAUD
            self.report_category = State.FRAUD
            self.priority = LOWER_PRIORITY
            return self.classify_fraud()
        elif message.content == "5":
            self.state = State.MISINFORMATION
            self.report_category = State.MISINFORMATION
            self.priority = LOWER_PRIORITY
            return self.classify_misinformation()
        elif message.content == "6":
            self.state = State.HATE_HARASSMENT
            self.report_category = State.HATE_HARASSMENT
            self.priority = LOWER_PRIORITY
            return self.classify_hate_harassment()
        elif message.content == "7":
            self.report_category = State.CSAM
            self.priority = HIGHER_PRIORITY
            return self.complete_report()
        elif message.content == "8":
            self.state = State.INTELLECTUAL
            self.report_category = State.INTELLECTUAL
            self.priority = LOWER_PRIORITY
            return self.classify_intellectual()
        else:
            self.state = State.ILLICIT_TRADE_SUBSTANCES
            self.report_category = State.ILLICIT_TRADE_SUBSTANCES
            self.priority = LOWER_PRIORITY
            return self.classify_illicit_trade()

    def complete_report(self):
        self.state = State.BLOCK_USER
        self.report_status = "pending"

        try:
            self.save_report(self.client.db_cursor, self.client.db_connection)
            reply = "Thank you for submitting a report. Our content moderation team will review the report and take appropriate action. This may include contacting local authorities.\n\n"
            reply += f"Would you like to block `{self.reported_user}`?\n"
            reply += "You will no longer be able to interact with them.\n"
            reply += "Please reply with `yes` or `no`."
            return [reply]
        except Exception as e:
            logger.error(f"Failed to save the report to the database: {e}")
            return ["Failed to save the report to the database. Please try again later."]

    def classify_offensive_content(self):
        reply = "What kind of offensive content are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Self-harm or suicidal content.\n"
        reply += "2. Terrorism.\n"
        reply += "3. Threats or depictions of violence and abuse.\n"
        reply += "4. Death or severe injury.\n"
        return [reply]

    def classify_nudity(self):
        reply = "What kind of sexually explicit content are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Adult nudity or pornography.\n"
        reply += "2. Sexual harassment or abuse.\n"
        return [reply]

    def classify_fraud(self):
        reply = "What kind of fraud or scam are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Impersonation.\n"
        reply += "2. Romance.\n"
        reply += "3. Financial.\n"
        return [reply]

    def classify_misinformation(self):
        reply = "What kind of misinformation are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Health.\n"
        reply += "2. Climate.\n"
        reply += "3. Political.\n"
        return [reply]

    def classify_hate_harassment(self):
        reply = "What kind of hate or harassment are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Bullying.\n"
        reply += "2. Revealing private information.\n"
        reply += "3. Hate speech.\n"
        reply += "4. Stalking.\n"
        return [reply]

    def classify_intellectual(self):
        reply = "What kind of intellectual property theft are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Infringes my copyright.\n"
        reply += "2. Infringes my trademark.\n"
        return [reply]

    def classify_illicit_trade(self):
        reply = "What kind of illicit trade and substances are you reporting? Please select the number corresponding to the appropriate category.\n\n"
        reply += "1. Illegal drug use or sale.\n"
        reply += "2. Sale or promotion of counterfeit goods.\n"
        reply += "3. Black market and smuggling.\n"
        return [reply]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    async def handle_block(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.BLOCK_COMPLETE

        if message.content.startswith(self.START_KEYWORD):
            return await self.handle_message(message)

        if message.content.startswith(self.BLOCK_KEYWORD):
            self.state = State.BLOCK_START
            reply = "Thank you for starting the blocking process.\n"
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the username of the user you want to block.\n"
            reply += "You can obtain this by right-clicking the user, clicking `Profile,` and copying the username."
            self.state = State.AWAITING_BLOCK
            return [reply]

        if self.state == State.AWAITING_BLOCK:
            self.reported_user = message.content.lower()
            reply = f"Please confirm that you would like to block `{self.reported_user}`.\n"
            reply += "You will no longer be able to interact with them.\n"
            reply += "Please reply with `yes` or `no`."
            self.state = State.AWAITING_BLOCK_CONFIRM
            return [reply]

        if self.state == State.AWAITING_BLOCK_CONFIRM:
            if message.content.lower() == "yes":
                reply = f"Thank you. `{self.reported_user}` has been blocked."
            else:
                reply = f"Thank you. `{self.reported_user}` has not been blocked."
            self.state = State.BLOCK_COMPLETE
            return [reply]

        return []

    def block_complete(self):
        return self.state == State.BLOCK_COMPLETE

    def save_report(self, db_cursor, db_connection):
        '''
        This function saves the report to the database.
        '''
        report_data = {
            "reported_user_id": self.reported_user_id,
            "reporter_user_id": self.reporter_user_id,
            "reportee": self.reportee,
            "reported_user": self.reported_user,
            "reported_message": self.reported_message,
            "report_category": self.report_category,
            "report_subcategory": self.report_subcategory,
            "additional_details": self.additional_details,
            "priority": self.priority,
            "report_status": self.report_status,
            "time_reported": self.time_reported.strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            logger.debug(f"Saving report to DB: {report_data}")
            db_cursor.execute('''
                INSERT INTO reports (reported_user_id, reporter_user_id, reportee, reported_user, reported_message, 
                                     report_category, report_subcategory, additional_details, priority, report_status, time_reported)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (report_data["reported_user_id"], report_data["reporter_user_id"], report_data["reportee"], report_data["reported_user"],
                  report_data["reported_message"], report_data["report_category"], report_data["report_subcategory"],
                  report_data["additional_details"], report_data["priority"], report_data["report_status"], report_data["time_reported"]))
            db_connection.commit()
        except Exception as e:
            logger.error(f"Failed to save the report to the database: {e}")
            db_connection.rollback()
