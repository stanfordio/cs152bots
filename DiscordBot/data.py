from datetime import datetime


class ReportData:
    SUMMARY = """
Message:
    Author: {offender}
    Content: {content}

Report Details:
    Reason: {reason}
    Abuse Type: {abuse_type}
    Abuse Description: {abuse_description}
    Unwanted Requests: {unwanted_requests}
    Multiple Requests: {multiple_requests}
    Approximate Requests: {approximate_requests}
    Complied with Requests: {complied_with_requests}

Additional Information:
    Minor Participation: {minor_participation}
    Contained you or the person on behalf of whom this report is being filed: {contain_yourself}
    Encouraged self-harm: {encourage_self_harm}
    Additional information provided: {additional_info}
"""

    MODERATOR_NOTES = """
Moderator Notes:
    Priority: {priority}
    Created at: {date} (UTC)
    Completed at: {completed_at} (UTC)

    Created by: {reporter}
    On behalf of: {on_behalf_of}
    
    Reported User Blocked: {block_user}
"""

    def __init__(self):
        self.report_started_at = datetime.utcnow()
        self.report_completed_at = None
        self.reporter = None
        self.message = None
        self.on_behalf_of = None
        self.reason = None
        self.abuse_type = None
        self.abuse_description = None
        self.unwanted_requests = None
        self.multiple_requests = None
        self.approximate_requests = None
        self.complied_with_requests = None
        self.minor_participation = None
        self.contain_yourself = None
        self.encourage_self_harm = None
        self.additional_info = None
        self.blocked_user = None

    @property
    def priority(self) -> str:
        """
        Naive priority calculation based on certain fields.
        """
        risk = sum(
            [
                # can be None
                self.multiple_requests * 2 if self.multiple_requests else 0,
                self.minor_participation * 3,
                self.contain_yourself,
                # can be None (skipped)
                self.encourage_self_harm * 3 if self.encourage_self_harm else 0,
                self.blocked_user,
            ]
        )

        if risk <= 1:
            return "Low"

        if risk == 2:
            return "Medium"

        return "High"

    @property
    def summary(self) -> str:
        """
        Generate a summary of the report.
        """
        return ReportData.SUMMARY.format(
            offender=self.message.author.name,
            content=self.message.content,
            reason=self.reason,
            abuse_type=self.abuse_type,
            abuse_description=self.abuse_description,
            unwanted_requests=self._human_readable(self.unwanted_requests),
            multiple_requests=self._human_readable(self.multiple_requests),
            approximate_requests=self._human_readable(self.approximate_requests),
            complied_with_requests=self._human_readable(self.complied_with_requests),
            minor_participation=self._human_readable(self.minor_participation),
            contain_yourself=self._human_readable(self.contain_yourself),
            encourage_self_harm=self._human_readable(self.encourage_self_harm),
            additional_info=self._human_readable(self.additional_info),
        )

    @property
    def moderator_summary(self) -> str:
        """
        Generate a summary of the report for the moderator.
        """
        return (
            "New user report created. Please review the following report and take"
            " necessary action.\n"
            + "```"
            + ReportData.MODERATOR_NOTES.format(
                priority=self.priority,
                date=self.report_started_at,
                completed_at=self.report_completed_at,
                reporter=self.reporter.name,
                on_behalf_of=self.on_behalf_of if self.on_behalf_of else "themselves",
                block_user=self._human_readable(self.blocked_user),
            )
            + self.summary
            + "```"
        )

    @property
    def user_summary(self) -> str:
        """
        Generate a summary of the report for the user.
        """
        return "```" + self.summary + "```"

    def _human_readable(self, value: str) -> str:
        """
        Convert a boolean values and None to human readable strings.
        """
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if value is None:
            return "N/A"
        return value
