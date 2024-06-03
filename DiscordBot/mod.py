import logging
import discord
from report import Report
import sqlite3
from enum import Enum, auto
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class State(Enum):
    REVIEW_START = auto()
    REVIEWING_VIOLATION = auto()
    REVIEWING_NONVIOLATION = auto()
    REVIEWING_ADVERSARIAL_REPORTING = auto()
    REVIEWING_LEGALITY_DANGER = auto()
    REVIEWING_FRAUD_SCAM_1 = auto()
    REVIEWING_FRAUD_SCAM_2 = auto()
    REVIEWING_MISLEADING_OFFENSIVE_1 = auto()
    REVIEWING_MISLEADING_OFFENSIVE_2 = auto()
    REVIEWING_FURTHER = auto()
    REVIEWING_ESCALATE = auto()
    REVIEW_COMPLETE = auto()
    REVIEW_ANOTHER = auto()
    REVIEW_BAN = auto()
    REVIEW_UNBAN = auto()
    AWAITING_UNBAN_CONFIRM = auto()


class Review:
    START_KEYWORD = "review"
    UNBAN_KEYWORD = "unban"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.message = None
        self.report = None
        self.banned_users_list = []

    async def handle_review(self, message):
        logger.debug(
            f"Handling review with state: {self.state} and message: {message.content}")

        reply = ""

        if message.content.startswith(self.START_KEYWORD):
            pending_reports = self.fetch_pending_reports()
            if not pending_reports:
                reply = "There are no pending reports to review.\n"
                return [reply]
            reply = f"Thank you for starting the reviewing process. There are {len(pending_reports)} pending reports to review.\n"
            reply += self.start_review(pending_reports)
            logger.debug(f"Replying to review start, state: {self.state}")
            return [reply]

        if message.content.startswith(self.UNBAN_KEYWORD):
            return await self.handle_unban(message)

        if self.state == State.AWAITING_UNBAN_CONFIRM:
            return await self.handle_unban_confirm(message)

        if self.state == State.REVIEWING_VIOLATION:
            logger.debug("State: REVIEWING_VIOLATION")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_VIOLATION state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                logger.debug("Removing violating content")
                reply = "Violating content has been removed.\n"
                reply += "Was the content illegal? Does the content pose an immediate danger? Please respond with `yes` or `no`."
                self.state = State.REVIEWING_LEGALITY_DANGER
                logger.debug(f"State changed to: {self.state}")
                return [reply]
            else:
                reply = "Do you suspect the content was reported maliciously? Please respond with `yes` or `no`."
                self.state = State.REVIEWING_NONVIOLATION
                logger.debug(f"State changed to: {self.state}")
                return [reply]

        if self.state == State.REVIEWING_NONVIOLATION:
            logger.debug("State: REVIEWING_NONVIOLATION")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_NONVIOLATION state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = "Do you suspect there was coordinated reporting from multiple actors? Please respond with `yes` or `no`."
                self.state = State.REVIEWING_ADVERSARIAL_REPORTING
                logger.debug(f"State changed to: {self.state}")
            else:
                reply = "Thank you. No further action will be taken.\n\n"
                self.mark_report_resolved()
                reply += self.prompt_new_review()
            return [reply]

        if self.state == State.REVIEWING_ADVERSARIAL_REPORTING:
            logger.debug("State: REVIEWING_ADVERSARIAL_REPORTING")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_ADVERSARIAL_REPORTING state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = f"Reported user `{self.report.reported_user}` has been temporarily banned.\n"
                reply += "This report will be escalated to higher moderation teams for further review.\n\n"
            else:
                reply = f"Reported user `{self.report.reported_user}` has been temporarily banned.\n"
            self.mark_report_resolved()
            reply += self.prompt_new_review()
            return [reply]

        if self.state == State.REVIEWING_LEGALITY_DANGER:
            logger.debug("State: REVIEWING_LEGALITY_DANGER")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_LEGALITY_DANGER state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = "This message will be submitted to local authorities.\n"
                reply += f"Reported user `{self.report.reported_user}` has been permanently banned.\n\n"
                self.ban_user(self.report.reported_user_id, message.author.id)
                self.mark_report_resolved()
                reply += self.prompt_new_review()
                return [reply]
            else:
                reply = "Did the reported message violate policies on fraud or scam? Please respond with `yes` or `no`."
                self.state = State.REVIEWING_FRAUD_SCAM_1
                logger.debug(f"State changed to: {self.state}")
                return [reply]

        if self.state == State.REVIEWING_FRAUD_SCAM_1:
            logger.debug("State: REVIEWING_FRAUD_SCAM_1")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_FRAUD_SCAM_1 state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                if self.report.additional_details:
                    reply = "The report contains these additional details.\n\n"
                    reply += self.report.additional_details + "\n\n"
                    reply += "Do the additional details contain any harmful links? Please respond with `yes` or `no`."
                    self.state = State.REVIEWING_FRAUD_SCAM_2
                    logger.debug(f"State changed to: {self.state}")
                    return [reply]
                if not self.report.additional_details:
                    reply = f"Reported user `{self.report.reported_user}` has been permanently banned.\n\n"
                    self.ban_user(self.report.reported_user_id,
                                  message.author.name)
                    self.mark_report_resolved()
                    reply += self.prompt_new_review()
                    return [reply]
            else:
                reply = "Was the reported message misleading or offensive? Please respond with `yes` or `no`."
                self.state = State.REVIEWING_MISLEADING_OFFENSIVE_1
                logger.debug(f"State changed to: {self.state}")
                return [reply]

        if self.state == State.REVIEWING_FRAUD_SCAM_2:
            logger.debug("State: REVIEWING_FRAUD_SCAM_2")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_FRAUD_SCAM_2 state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = "The harmful links have been blacklisted.\n"
            reply += f"Reported user `{self.report.reported_user}` has been permanently banned.\n\n"
            self.ban_user(self.report.reported_user_id, message.author.name)
            self.mark_report_resolved()
            reply += self.prompt_new_review()
            return [reply]

        if self.state == State.REVIEWING_MISLEADING_OFFENSIVE_1:
            logger.debug("State: REVIEWING_MISLEADING_OFFENSIVE_1")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_MISLEADING_OFFENSIVE_1 state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = "Does the user have a history of violation?\n"
                reply += "Please respond with `yes` or `no`."
                self.state = State.REVIEWING_MISLEADING_OFFENSIVE_2
                logger.debug(f"State changed to: {self.state}")
                return [reply]
            else:
                reply = "The report has not been classified into any existing categories.\n"
                reply += "Please provide details about your review.\n\n"
                self.state = State.REVIEWING_FURTHER
                logger.debug(f"State changed to: {self.state}")
                return [reply]

        if self.state == State.REVIEWING_MISLEADING_OFFENSIVE_2:
            logger.debug("State: REVIEWING_MISLEADING_OFFENSIVE_2")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_MISLEADING_OFFENSIVE_2 state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = f"Reported user `{self.report.reported_user}` has been flagged.\n\n"
            else:
                reply = f"Reported user `{self.report.reported_user}` has been warned.\n\n"
            self.mark_report_resolved()
            reply += self.prompt_new_review()
            return [reply]

        if self.state == State.REVIEWING_FURTHER:
            logger.debug("State: REVIEWING_FURTHER")
            reply = "Thank you for providing details about your review.\n\n"
            reply += "Is further action necessary to review the violating content? Please respond with `yes` or `no`.\n\n"
            self.state = State.REVIEWING_ESCALATE
            logger.debug(f"State changed to: {self.state}")
            return [reply]

        if self.state == State.REVIEWING_ESCALATE:
            logger.debug("State: REVIEWING_ESCALATE")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_ESCALATE state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                reply = "Thank you. This report will be escalated to a higher moderation team for further review.\n\n"
            else:
                reply = "Thank you. No further action will be taken.\n\n"
            self.mark_report_resolved()
            reply += self.prompt_new_review()
            return [reply]

        if self.state == State.REVIEW_ANOTHER:
            logger.debug("State: REVIEW_ANOTHER")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEW_ANOTHER state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            return [self.start_review(self.fetch_pending_reports())]

        return []

    async def handle_unban(self, message):
        banned_users = self.get_banned_users()
        if not banned_users:
            return ["There are no banned users."]

        reply = "Here are the users you have banned:\n"
        for idx, user in enumerate(banned_users):
            user_info = await self.client.fetch_user(user['banned_user_id'])
            reply += f"{idx + 1}. {user_info.name}#{user_info.discriminator} (banned on {user['time_banned']})\n"

        reply += "\nPlease type the number of the user you want to unban or type `cancel` to cancel."
        self.state = State.AWAITING_UNBAN_CONFIRM
        self.banned_users_list = banned_users
        return [reply]

    def get_banned_users(self):
        try:
            self.client.db_cursor.execute(
                'SELECT banned_user_id, time_banned FROM bans')
            rows = self.client.db_cursor.fetchall()
            return [{'banned_user_id': row[0], 'time_banned': row[1]} for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve banned users: {e}")
            return []

    async def handle_unban_confirm(self, message):
        try:
            logger.debug(
                f"Unban confirmation received with message: {message.content}")
            unban_idx = int(message.content) - 1
            if unban_idx < 0 or unban_idx >= len(self.banned_users_list):
                return ["Invalid selection. Please type the number of the user you want to unban or type `cancel` to cancel."]

            banned_user_id = self.banned_users_list[unban_idx]['banned_user_id']
            logger.debug(f"Unbanning user with ID: {banned_user_id}")

            self.client.db_cursor.execute(
                'DELETE FROM bans WHERE banned_user_id = ?', (banned_user_id,))
            self.client.db_connection.commit()
            self.state = State.REVIEW_COMPLETE
            return [f"User `{banned_user_id}` has been unbanned."]

        except ValueError:
            return ["Invalid input. Please type the number of the user you want to unban or type `cancel` to cancel."]
        except sqlite3.Error as e:
            logger.error(f"Failed to unban the user: {e}")
            self.client.db_connection.rollback()
            return ["Failed to unban the user. Please try again later."]

    def start_review(self, pending_reports):
        logger.debug("Starting review")
        reply = "Here is the next report to review.\n\n"
        self.report = pending_reports.pop(0)

        reply += f"User reported: `{self.report.reported_user}`\n"
        reply += f"Message reported: `{self.report.reported_message}`\n"
        reply += f"Report category: {self.report.report_category}\n"
        reply += f"Report subcategory: {self.report.report_subcategory}\n"
        reply += f"Additional details filed by reporting: {self.report.additional_details}\n\n"

        reply += f"Is this in violation of platform policies? Please respond with `yes` or `no`."
        self.state = State.REVIEWING_VIOLATION
        logger.debug(f"State changed to: {self.state}")
        return reply

    def prompt_new_review(self):
        logger.debug("Prompting new review")
        reply = "Thank you for reviewing this report.\n"
        pending_reports = self.fetch_pending_reports()
        if not pending_reports:
            reply += "There are no more pending reports to review.\n"
            self.state = State.REVIEW_COMPLETE
            logger.debug(f"State changed to: {self.state}")
        else:
            reply += f"There are {len(pending_reports)} pending reports to review. Would you like to review another report?\n"
            self.state = State.REVIEW_ANOTHER
            logger.debug(f"State changed to: {self.state}")

        return reply

    def fetch_pending_reports(self):
        logger.debug("Fetching pending reports")
        self.client.db_cursor.execute('''
            SELECT report_id, reported_user_id, reporter_user_id, reportee, reported_user, reported_message, 
                   report_category, report_subcategory, additional_details, priority, report_status, time_reported 
            FROM reports WHERE report_status = 'pending' ORDER BY priority, time_reported
        ''')
        pending_reports = self.client.db_cursor.fetchall()
        return [
            Report(
                report_id=row[0],
                reported_user_id=row[1],
                reporter_user_id=row[2],
                reportee=row[3],
                reported_user=row[4],
                reported_message=row[5],
                report_category=row[6],
                report_subcategory=row[7],
                additional_details=row[8],
                priority=row[9],
                report_status=row[10],
                time_reported=row[11]
            ) for row in pending_reports
        ]

    def mark_report_resolved(self):
        logger.debug(f"Marking report {self.report.report_id} as resolved")
        try:
            self.client.db_cursor.execute('''
                UPDATE reports
                SET report_status = 'resolved'
                WHERE report_id = ?
            ''', (self.report.report_id,))
            self.client.db_connection.commit()
        except sqlite3.Error as e:
            logger.error(f"Error marking report as resolved: {e}")
            self.client.db_connection.rollback()

    def ban_user(self, banned_user_id, moderator_user_id):
        try:
            # Check if the user is already banned
            self.client.db_cursor.execute(
                'SELECT * FROM bans WHERE banned_user_id = ?', (banned_user_id,))
            if self.client.db_cursor.fetchone():
                logger.warning(f"User {banned_user_id} is already banned.")
                return

            self.client.db_cursor.execute('''
                INSERT INTO bans (banned_user_id, moderator_user_id, time_banned)
                VALUES (?, ?, ?)
            ''', (banned_user_id, moderator_user_id, datetime.now()))
            self.client.db_connection.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to ban the user: {e}")
            self.client.db_connection.rollback()
