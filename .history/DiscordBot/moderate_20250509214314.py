from enum import Enum, auto

class ModState(Enum):
    MOD_START = auto()
    AWAITING_DECISION = auto()
    AWAITING_SKIP_REASON = auto()
    AWAITING_SUMMARY_CONFIRM = auto()
    AWAITING_ACTION = auto()
    REVIEW_COMPLETE = auto()

class ModeratorReview:
    def __init__(self):
        self.state = ModState.MOD_START

        self.message_guild_id = None

        self.original_report = None

        self.report_type = None
        self.disinfo_type = None
        self.disinfo_subtype = None
        self.imminent = None
        self.filter = False

        self.reported_author_metadata = None
        self.reported_content_metadata = None
        self.message = None

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
                self.state = ModState.AWAITING_SUMMARY_CONFIRM
                reply = "This content was reported as " + self.report_type + ".\n"
                reply += "Disinfo category: " + str(self.disinfo_type) + " - " + str(self.disinfo_subtype) + "\n"
                if self.imminent:
                    reply += "Potential imminent harm: " + self.imminent + "\n"
                if self.filter:
                    reply += "User requested filtering/blocking.\n"
                reply += "Author metadata: " + str(self.reported_author_metadata) + "\n"
                reply += "Content metadata: " + str(self.reported_content_metadata) + "\n\n"
                reply += "Type any key to continue."
                return [reply]

            elif message.content.lower() == "skip":
                self.state = ModState.AWAITING_SKIP_REASON
                return [
                    "Please select a reason for skipping:",
                    "1. Personal mental health",
                    "2. Conflict of interest (recusal)",
                    "3. Uncertainty"
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
                self.action_taken = "Skipped"
                return [f"You skipped this review due to: {self.skip_reason}.", "Returning to queue."]
            else:
                return ["Please choose a valid skip reason: 1, 2, or 3."]

        if self.state == ModState.AWAITING_SUMMARY_CONFIRM:
            self.state = ModState.AWAITING_ACTION
            return [
                "What action would you like to take on this content?",
                "1. Remove content",
                "2. Allow content"
            ]

        if self.state == ModState.AWAITING_ACTION:
            if message.content == "1":
                self.action_taken = "Removed"
                print("TODO ACTUALLY REMOVE MESSAGE")
                self.state = ModState.REVIEW_COMPLETE
                return ["Content has been removed. Review complete."]
            elif message.content == "2":
                self.action_taken = "Allowed"
                self.state = ModState.REVIEW_COMPLETE
                return ["Content has been allowed. Review complete."]
            else:
                return ["Invalid action. Type 1 to Remove or 2 to Allow."]

        return []
    
    def get_message_guild_id(self):
        return self.message_guild_id

    def get_report_type(self):
        return self.report_type

    def get_disinfo_type(self):
        return self.disinfo_type

    def get_disinfo_subtype(self):
        return self.disinfo_subtype

    def get_imminent(self):
        return self.imminent

    def get_filter(self):
        return self.filter

    def get_reported_author_metadata(self):
        return self.reported_author_metadata

    def get_reported_content_metadata(self):
        return self.reported_content_metadata

    def get_skip_reason(self):
        return self.skip_reason

    def get_action_taken(self):
        return self.action_taken

    def get_state(self):
        return self.state

    def set_report_info(self, report):
        self.report_type = report.get_report_type()
        self.disinfo_type = report.get_disinfo_type()
        self.disinfo_subtype = report.get_disinfo_subtype()
        self.imminent = report.get_imminent()
        self.filter = report.get_filter()

    def set_metadata(self, author_meta, content_meta, primer=None):
        self.reported_author_metadata = author_meta
        self.reported_content_metadata = content_meta

    def get_priority(self):
        if self.imminent in ["physical", "mental"]:
            return 0
        elif self.imminent == "financial":
            return 1
        else:
            return 2

    def is_review_complete(self):
        return self.state == ModState.REVIEW_COMPLETE

    def is_mod_start(self):
        return self.state == ModState.MOD_START

    def is_awaiting_decision(self):
        return self.state == ModState.AWAITING_DECISION

    def is_awaiting_skip_reason(self):
        return self.state == ModState.AWAITING_SKIP_REASON

    def is_awaiting_summary_confirm(self):
        return self.state == ModState.AWAITING_SUMMARY_CONFIRM

    def is_awaiting_action(self):
        return self.state == ModState.AWAITING_ACTION
