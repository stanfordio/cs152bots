from enum import Enum, auto
import discord
import re
from report import Report

class State(Enum):
    AWAITING_MESSAGE = auto()
    START = auto()
    THREAT_LEVEL = auto()
    DONE = auto()

class Moderate:
    def __init__(self, mod_channel, id, report, violations):
        self.state = State.AWAITING_MESSAGE
        self.mod_channel = mod_channel
        self.reported_id = id
        self.report = report
        if isinstance(report, Report):
            self.offender_id = report.reported_message['content'].author.id
        else:
            self.offender_id = report['content'].author.id
        self.violations = violations
        self.current_step = 0
        self.serious_threat = 0
        self.not_serious_threat = 0

    async def moderate_content(self, message, hateSpeech=True):
        if self.state == State.AWAITING_MESSAGE:
            reply = ""

            # step 0: moderator confirmed that the message is hateful conduct, now needs to classify it
            if self.current_step == 0:
                if message == "yes":
                    reply += "What kind of hateful conduct is it? "
                    reply += "Please say one of the following:\n"
                    slurs = "`slurs or symbols`: use of hateful slurs or symbols"
                    behavior = "`encouraging hateful behavior`: encouraging other users to partake in hateful behavior"
                    trauma = "`mocking trauma`: denying or mocking known hate crimes or events of genocide"
                    stereotypes = "`harmful stereotypes`: perpetuating discrimination against protected characteristics such as race, ethnicity, national origin, religious affiliation, sexual orientation, sex, gender, gender identity, serios disease, disability, or immigration status"
                    violence = "`threatening violence`: acts of credible threats of violence aimed at other users"
                    other = "`other`: the conduct does not fit into any of the above categories"
                    types = [slurs, behavior, trauma, stereotypes, violence, other]
                    reply += "\n".join(f"  • {type}" for type in types)
                    self.state = State.AWAITING_MESSAGE
                    self.current_step = 1
                    return reply
                elif message == "no":
                    reply += "This bot only accepts reports of hateful conduct. Please say `yes` if you would like to report hateful conduct, or `cancel` to cancel."
                else:
                    reply += "Please say `yes` or `no`."
                
            # step 1: moderator picked the relevant hate speech type
            if self.current_step == 1:
                reply = "You have classified this message as " + message + ". "
                if message == "threatening violence":
                    self.serious_threat = 1
                if message == "encouraging hateful behavior":
                    self.serious_threat = 1
                if message == "other":
                    self.not_serious_threat = 1
                if message == "slurs or symbols":
                    self.not_serious_threat = 1
                if message == "mocking trauma":
                    self.not_serious_threat = 1
                if message == "harmful stereotypes":
                    self.not_serious_threat = 1
            
                if self.not_serious_threat:
                    # Check how many times the user has violated the community guidelines
                    count = self.violations.get(self.offender_id, 0)
                    if count == 0 or count == 1:
                        reply += "We will remove the comment."
                    elif count == 2:
                        reply += f"We will remove the comment and mute {self.offender_id}'s account for 24 hours."
                    elif count >= 3:
                        reply += f"We will remove the comment and ban {self.offender_id}'s account."
                    self.current_step = 3
                elif self.serious_threat:
                    reply += "Provided your choices, this content may pose a serious and/or violent threat.\n"
                    reply += "The comment has been removed and the account has been banned.\n"
                    reply += "Do you believe that the offender violated the law or that someone is in need of immediate assistance? Please say 'yes' or 'no'."
                    self.state = State.AWAITING_MESSAGE
                    self.current_step = 2.5
                    return reply

            # step 2.5: moderator decides whether to involve law enforcement
            if self.serious_threat and self.current_step == 2.5:
                if message == "yes":
                    reply = "This report has been forwarded to both the Trust and Safey division and the proper authorities with highest priority. "
                    self.current_step = 3
                elif message == "no":
                    reply = "This report has been sent to Trust and Safey."  # if they say no, shouldn't we close the issue? why do we need to tell Trust and Safety?
                    self.current_step = 3
                else:
                    self.state = State.AWAITING_MESSAGE
                    reply = "This response is invalid. Please respond 'yes' or 'no'."
                    return reply
            
            # step 3: report is complete
            if self.current_step == 3:
                self.state = State.DONE
                reply += "\n\nThank you for reviewing this report. This report is now closed."
                return reply

            return reply
