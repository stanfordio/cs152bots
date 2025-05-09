from enum import Enum, auto

class ModState(Enum):
    MOD_START = auto()
    AWAITING_DECISION = auto()
    AWAITING_SKIP_REASON = auto()
    REVIEWING_REPORT = auto()
    AWAITING_ACTION = auto()
    REVIEW_COMPLETE = auto()

class ModeratorReview:
    def __init__(self):
        self.state = ModState.MOD_START

        self.report_type = None
        self.disinfo_type = None
        self.disinfo_subtype = None
        self.imminent = None
        self.filter = False

        self.reported_author_metadata = None
        self.reported_content_metadata = None
        self.relevant_primer = None
        
        self.skip_reason = None
        self.action_taken = None

    async def handle_message(self, message):
        if self.state == ModState.MOD_START:
            self.state = ModState.AWAITING_DECISION
            return [
                "New reported content available.",
                "Would you like to review it now?",
                "Type `yes` to begin review, or `skip` to pass."
            ]

        if self.state == ModState.AWAITING_DECISION:
            if message.content.lower() == "yes":
                self.state = ModState.REVIEWING_REPORT
                return self.get_report_summary()

            elif message.content.lower() == "skip":
                self.state = ModState.AWAITING_SKIP_REASON
                return [
                    "Please select a reason for skipping:",
                    "1. Personal mental health",
                    "2. Conflict of interest (recusal)",
                    "3. Uncertainty (request second opinion)"
                ]
            else:
                return ["Invalid response. Type `yes` or `skip`."]

        if self.state == ModState.AWAITING_SKIP_REASON:
            reasons = {
                "1": "Personal mental health",
                "2": "Conflict of interest",
                "3": "Uncertainty"
            }
            if message.content in reasons:
                self.skip_reason = reasons[message.content]
                self.state = ModState.REVIEW_COMPLETE
                return [f"You skipped this review due to: {self.skip_reason}.", "Returning to queue."]
            else:
                return ["Please choose a valid skip reason: 1, 2, or 3."]

        if self.state == ModState.REVIEWING_REPORT:
            self.state = ModState.AWAITING_ACTION
            return [
                "What action would you like to take on this content?",
                "1. Remove content",
                "2. Allow content"
            ]

        if self.state == ModState.AWAITING_ACTION:
            if message.content == "1":
                self.action_taken = "Removed"
                self.state = ModState.REVIEW_COMPLETE
                return ["Content has been removed. Review complete."]
            elif message.content == "2":
                self.action_taken = "Allowed"
                self.state = ModState.REVIEW_COMPLETE
                return ["Content has been allowed. Review complete."]
            else:
                return ["Invalid action. Type 1 to Remove or 2 to Allow."]

        return []

    def get_report_summary(self):
        summary = ["Beginning review:"]
        summary.append(f"Reported type: {self.report_type}")
        summary.append(f"Disinfo category: {self.disinfo_type} - {self.disinfo_subtype}")
        if self.imminent:
            summary.append(f"Potential imminent harm: {self.imminent}")
        if self.filter:
            summary.append("User requested filtering/blocking.")
        summary.append("\nMetadata:")
        summary.append(f"Author info: {self.reported_author_metadata}")
        summary.append(f"Post info: {self.reported_content_metadata}")
        summary.append(f"Primer: {self.relevant_primer}")
        summary.append("Type any key to continue.")
        return summary

    def set_report_info(self, report):
        self.report_type = report.get_report_type()
        self.disinfo_type = report.get_disinfo_type()
        self.disinfo_subtype = report.get_disinfo_subtype()
        self.imminent = report.get_imminent()
        self.filter = report.get_filter()

    def set_metadata(self, author_meta, content_meta, primer):
        self.reported_author_metadata = author_meta
        self.reported_content_metadata = content_meta
        self.relevant_primer = primer

    def get_final_decision(self):
        return self.action_taken
    def get_skip_reason(self):
        return self.skip_reason
    def is_review_complete(self):
        return self.state == ModState.REVIEW_COMPLETE
