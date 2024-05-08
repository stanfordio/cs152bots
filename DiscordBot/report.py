from enum import Enum, auto
import discord
import re

start_dialogue = "Please select a report reason"
start_options = [start_dialogue, "Spam", "Fake Account", "Harassment or Bullying", "Posting inappropriate things", "Scam", "Something else"]
spam_dialogue = "What is your reason for suspicion?"
spam_options = [spam_dialogue, "Fake Account", "Unsolicited Promotions", "Unrelated to the discord channel or anything that I've said"]
fake_account_dialogue = "Who is this person impersonating?"
fake_account_options = [fake_account_dialogue, "Pretending to be me", "Pretending to be someone I know", "Pretending to be a celebrity or public figure", "Pretending to be a business or organization", "Other"]
post_dialogue = "Select type of content this person is posting"
post_options = [post_dialogue, "Hate speech", "Adult nudity and sexual activity", "Child sexual exploitation, abuse, and nudity", "Violence and graphic content"]
scam_dialogue = "What did the user do?"
scam_options = [scam_dialogue, "Presented a suspicious investment opportunity", "Asked for password or other sensitive information", "Asked for money, even though we have never met", "User disappeared after money transaction"]
else_dialogue = "Please provide detailed descriptions"
else_options = [else_dialogue, "[Optional] Please attach any relevant screenshots that can help us investigate the issue."]
final_dialogue = "Thanks for reporting. Our content moderation team will review the profile and decide on the appropriate actions. \n\nWould you like to block this user?"
final_options = [final_dialogue, "yes", "no"]

class ReportState(Enum):
    Start = auto()
    Spam = auto()
    Fake = auto()
    Bully = auto()
    Post = auto()
    Scam = auto()
    Else = auto()
    Thanks = auto()
    End = auto()

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.flow_state = None
        self.last_step_question = None
        self.last_step_options = None
        self.case = {
            'notes': [],
            'message_details': None,
            'report_steps': []
        }

    def options_to_string(self, options):
        return options[0]+'\n\n' + '\n'.join(f"{i + 1}. {option}" for i, option in enumerate(options[1:]))

    async def handle_message(self, message: discord.Message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            self.case['notes'].append("Report cancelled by the user.")
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.case['notes'].append("User requested help.")
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
                original_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            self.state = State.MESSAGE_IDENTIFIED
            self.flow_state = ReportState.Start
            self.case['message_details'] = {
                'guild': guild.name,
                'channel': channel.name,
                'message_content': original_message.content,
                'user': original_message.author.name
            }
            self.case['report_steps'].append({
                'question': "Link to the message you want to report",
                'answer': message.id
            })
            self.last_step_question = start_options[0]
            self.last_step_options = start_options[1:]
            return [self.options_to_string(start_options)]

        if self.state == State.MESSAGE_IDENTIFIED:
            if self.flow_state is None:
                self.flow_state = ReportState.Start
                self.last_step_question = start_options[0]
                self.last_step_options = start_options[1:]
                return [self.options_to_string(start_options)]

            option_index = int(message.content) - 1
            user_choice = self.last_step_options[option_index]
            self.case['report_steps'].append({
                'question': self.last_step_question,
                'answer': user_choice
            })

            if self.flow_state == ReportState.Start:
                self.flow_state = [ReportState.Spam, ReportState.Fake, ReportState.Bully, ReportState.Post, ReportState.Scam,ReportState.Else][option_index]
                next_options = [spam_options, fake_account_options, final_options, post_options, scam_options, else_options][option_index]
                self.last_step_question = next_options[0]
                self.last_step_options = next_options[1:]
                return [self.options_to_string(next_options)]

            elif self.flow_state == ReportState.Spam:
                self.flow_state = [ReportState.Fake, ReportState.Thanks, ReportState.Thanks][option_index]
                next_options = [fake_account_options, final_options, final_options][option_index]
                self.last_step_question = next_options[0]
                self.last_step_options = next_options[1:]
                return [self.options_to_string(next_options)]

            elif self.flow_state == ReportState.Fake:
                self.flow_state = ReportState.Thanks
                next_options = final_options
                self.last_step_question = next_options[0]
                self.last_step_options = next_options[1:]
                return  [self.options_to_string(next_options)]

            elif self.flow_state == ReportState.Post:
                self.flow_state = ReportState.Thanks
                next_options = final_options
                self.last_step_question = next_options[0]
                self.last_step_options = next_options[1:]
                return  [self.options_to_string(next_options)]

            elif self.flow_state == ReportState.Scam:
                self.flow_state = ReportState.Thanks
                next_options = final_options
                self.last_step_question = next_options[0]
                self.last_step_options = next_options[1:]
                return [self.options_to_string(next_options)]

            elif self.flow_state in [ReportState.Bully, ReportState.Thanks]:
                self.state = State.REPORT_COMPLETE
                self.flow_state = ReportState.End
                next_options = final_options
                self.last_step_question = next_options[0]
                self.last_step_options = next_options[1:]
                print(user_choice)
                if user_choice == 'yes':
                    # Block the user
                    return ["The user has been blocked."]
                else:
                    return ["Thank you"]

            return ["Unexpected state in reporting flow. Type `cancel` and start a new report."]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE




    

