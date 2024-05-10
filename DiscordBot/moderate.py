from enum import Enum, auto
import discord
import re

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
        self.offender_id = report.reported_message['content'].author.id
        self.violations = violations
        self.current_step = 0
        self.serious_threat = 0
        self.not_serious_threat = 0

    async def moderate_content(self, message, hateSpeech=True):
        if self.state == State.AWAITING_MESSAGE:                  
            # step 1: user confirmed that the message is hateful conduct, now needs to classify it
            reply = ""
            print(self.current_step)
            if self.current_step == 0:
                if message == "yes":
                    reply += "Thank you for confirming that this is hateful conduct. "
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
                    self.current_step += 1

                if message == "no":
                    reply += "This bot only accepts reports of hateful conduct. Please say `yes` if you would like to report hateful conduct, or `cancel` to cancel."

                else:
                    reply += "Please say `yes` or `no`. If you would like to cancel your report, say `cancel`."
                
            # step 2: user picked the relevant hate speech type, now decides whether to submit or continue
            elif self.current_step == 1:
                # we need to add this message content to the final message that is submitted
                reply = "You have classified this message as " + message + ". "
                if message == "threatening violence":
                    self.serious_threat = 1
                if message == "encouraging harmful behavior":
                    self.serious_threat = 1
                if message == "other":
                    self.not_serious_threat = 1
                if message == "slurs or symbols":
                    self.not_serious_threat = 1
                if message == "mocking trauma":
                    self.not_serious_threat = 1
                if message == "harmful stereotypes":
                    self.not_serious_threat = 1
                self.current_step += 1
            
            elif self.not_serious_threat and self.current_step == 2:
                    # Check how many times the user has violated the community guidelines
                    count = self.violations.get(self.offender_id, 0)
                    if count == 1:
                        reply = "We will remove the comment."
                    elif count == 2:
                        reply = f"We will remove the comment and mute {self.offender_id}'s account for 24 hours."
                    elif count >= 3:
                        reply = f"We will remove the comment and ban {self.offender_id}'s account."
                    self.current_step += 1
        
            # elif self.not_serious_threat and self.current_step == 3:
            #     if message == "1":
            #         reply = "We will remove the comment."
            #     elif message == "2":
            #         reply = f"We will remove the comment and mute {self.offender_id}'s account for 24 hours."
            #     elif message == "3":
            #         reply = f"We will remove the comment and ban {self.offender_id}'s account."
            #     else:
                    #reply = "Invalid action."

            elif self.serious_threat and self.current_step == 2:
                    reply = "Provided your choices, this content may pose a serious and/or violent threat.\n"
                    reply += "The comment has been removed and the account has been banned.\n"
                    reply += "Do you suspect that the offedner commited an illegal crime or someone is in need of immediate assistance?"
                    self.current_step += 1

            elif self.serious_threat and self.current_step == 3:
                if message == "yes":
                    reply = "This report has been sent to Trust and Safey and the proper authorities with highest priority. "
                elif message == "no":
                    reply = "This report has been sent to Trust and Safey."
                else:
                    reply = "This respons is invalid. Please respond 'yes' or 'no'."

            return reply
