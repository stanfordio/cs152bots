from enum import Enum, auto
import logging
import discord
from report import Report
import sqlite3

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


class Review:
    START_KEYWORD = "review"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.message = None
        self.report = None

    async def handle_review(self, message):
        logger.debug(
            f"Handling review with state: {self.state} and message: {message.content}")

        if message.content.startswith(self.START_KEYWORD):
            pending_reports = self.fetch_pending_reports()
            if not pending_reports:
                reply = "There are no pending reports to review.\n"
                return [reply]
            reply = f"Thank you for starting the reviewing process. There are {len(pending_reports)} pending reports to review.\n"
            reply += self.start_review(pending_reports)
            logger.debug(f"Replying to review start, state: {self.state}")
            return [reply]

        if self.state == State.REVIEWING_VIOLATION:
            logger.debug("State: REVIEWING_VIOLATION")
            if message.content.lower() not in ["yes", "no"]:
                logger.debug(
                    f"Invalid response in REVIEWING_VIOLATION state: {message.content}")
                return ["Please respond with `yes` or `no`."]

            if message.content.lower() == "yes":
                logger.debug("Removing violating content")
                # await self.report.reported_message.delete()
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
