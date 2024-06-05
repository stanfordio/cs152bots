from enum import Enum, auto
import discord
import json
import re
from supabase import create_client, Client

with open("tokens.json", "r") as f:
    tokens = json.load(f)

supabase_url = tokens.get("SUPABASE_URL")
supabase_key = tokens.get("SUPABASE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_INITIAL_REASON = auto()
    AWAITING_NUDITY_REASON = auto()
    AWAITING_MINOR_INVOLVEMENT_ANSWER = auto()
    AWAITING_MET_IN_PERSON_ANSWER = auto()
    AWAITING_EXPLANATION_INPUT = auto()
    AWAITING_NUDITY_EXPLANATION_INPUT = auto()
    AWAITING_FINAL_ADDITIONAL_INFORMATION = auto()
    AWAITING_BLOCK_ANSWER = auto()
    REPORT_COMPLETE = auto()

    
class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    EXPLANATION_INPUT_LIMIT = 300

    YES_NO_OPTIONS = [
        "Yes",
        "No"
    ]
    INITIAL_OPTIONS = [
        "Nudity or sexual activity",
        "Terrorism",
        "Harassment",
        "Hate Speech",
        "Spam",
        "Selling of illegal goods",
        "Something else"
    ]
    NUDITY_OPTIONS = [
        "They are threatening to share intimate pictures of me or someone else",
        "They sent me intimate images of themselves or of someone else",
        "They asked for intimate images of me or someone else",
        "Something else"
    ]

    REPORT_COMPLETE_OTHER_MESSAGE = "Thank you for helping us keep our community safe! We will investigate the matter and follow up as needed."
    REPORT_COMPLETE_SEXTORTION_MESSAGE = '''Thank you for helping us keep our community safe! We will investigate the matter and follow up as needed.
    In the meantime, we recommend the following:
    Stop responding to their messages, but do not delete the chat.
    If someone is in danger, contact law enforcement immediately.
    You are not alone and it is not your fault this is happening.
    If you know or suspect intimate images of you or someone under 18 have been leaked, visit Take It Down (https://takeitdown.ncmec.org/) for help.
    Take care of yourself and loved ones. [link to platform's mental health resources]'''

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.user = None
        self.message = None
        self.user_id = None
        self.message_link = None
        self.reason = []

    async def submit_report(self):
        if not all([self.user_id, self.user, self.message_link, self.reason, self.message]):
            if self.user:
                await self.user.send("Report cannot be submitted as some information is missing.")
            else:
                pass
            return

        mod_channel = discord.utils.get(self.client.get_all_channels(), name="group-29-mod")
        if mod_channel:
            report_message = "**New Report Submitted**\n\n"
            report_message += f"**Reported By:** <@{self.user_id}>\n"
            report_message += f"**Reported User:** <@{self.message.author.id}> ({self.message.author.name}#{self.message.author.discriminator})\n\n"
            report_message += f"**Reported Message:**\n```{self.message.content}```\n"
            report_message += f"**Message Link:** {self.message_link}\n\n"
            report_message += "**Reason(s):**\n"
            for reason in self.reason:
                report_message += f"- {reason}\n"

            report_message += "\nThere is a new report on the queue. Use the `eval` command to begin the evaluation process.\n\n"

            await mod_channel.send(report_message)
            # TODO add to queue

            await self.user.send("Our moderators will review your report and take appropriate action.")

            # Update the existing reports to set current_report to false
            supabase.table('User').update({'current_report': False}).eq('current_report', True).execute()

            # Insert the report data into the Supabase database
            reasons_text = ', '.join(self.reason)
            data = {
                'reported_user': f'{self.message.author.name}#{self.message.author.discriminator}',
                'current_report': True,
                'reported_by': str(self.user),
                'reported_message': self.message.content,
                'message_link': self.message_link,
                'reasons': reasons_text,
                'message_channel': self.message.channel.name
            }
            supabase.table('User').insert(data).execute()

        else:
            await self.user.send("Sorry, an error occurred while submitting your report. Please try again later or contact a moderator directly.")

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''
        reply = ""
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
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
            self.user = message.author
            self.user_id = message.author.id
            self.message_link = message.content

            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
                self.message = message

            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            self.state = State.AWAITING_INITIAL_REASON

            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```",
                    self.create_options_list("Select the reason for reporting this message. Don't worry, the person you are reporting against won't know it was you.",
                                             self.INITIAL_OPTIONS)]

        if self.state == State.AWAITING_INITIAL_REASON:
            i = self.get_index(message, self.INITIAL_OPTIONS)
            self.reason.append(self.INITIAL_OPTIONS[i])

            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                self.state = State.AWAITING_NUDITY_REASON
                reply = self.create_options_list("Please select which subtype of abuse happened:",
                                                 self.NUDITY_OPTIONS)
            elif i == 6:
                self.state = State.AWAITING_EXPLANATION_INPUT
                reply = f"Please tell us what happened ({self.EXPLANATION_INPUT_LIMIT} word limit)"
            else:
                self.state = State.AWAITING_FINAL_ADDITIONAL_INFORMATION
                reply = f"Please add any additional information you think is relevant ({self.EXPLANATION_INPUT_LIMIT} word limit)."
            return [reply]

        if self.state == State.AWAITING_NUDITY_REASON:
            i = self.get_index(message, self.NUDITY_OPTIONS)
            self.reason.append(self.NUDITY_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: give priority 1
                pass
            elif i == 1:
                # TODO: give priority 3
                pass
            elif i == 2:
                # TODO: give priority 2
                pass
            if i == 3:
                self.state = State.AWAITING_NUDITY_EXPLANATION_INPUT
                reply = f"Please tell us what happened ({self.EXPLANATION_INPUT_LIMIT} word limit)"
            else:
                self.state = State.AWAITING_MINOR_INVOLVEMENT_ANSWER
                reply = self.create_options_list("Does it involve someone under 18, either you or someone else?",
                                                 self.YES_NO_OPTIONS)
            return [reply]

        if self.state == State.AWAITING_MINOR_INVOLVEMENT_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: add yes to moderator report
                pass
            if i == 1:
                # TODO: add no to moderator report
                pass
            self.reason.append('Minor involved: ' + self.YES_NO_OPTIONS[i])
            self.state = State.AWAITING_MET_IN_PERSON_ANSWER
            reply = self.create_options_list("Have you or the person you are reporting on behalf met them in person?",
                                             self.YES_NO_OPTIONS)
            return [reply]

        if self.state == State.AWAITING_MET_IN_PERSON_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            self.reason.append('Met in person: ' + self.YES_NO_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: add yes to moderator report, give highest priority 1 if minor?
                pass
            if i == 1:
                # TODO: add no to moderator report
                pass
            self.state = State.AWAITING_FINAL_ADDITIONAL_INFORMATION
            reply = f"Please add any additional information you think is relevant ({self.EXPLANATION_INPUT_LIMIT} word limit)."
            return [reply]
        
        if self.state == State.AWAITING_EXPLANATION_INPUT:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                self.reason.append('Something else: ' + message.content)
                self.state = State.AWAITING_FINAL_ADDITIONAL_INFORMATION
                reply = f"Please add any additional information you think is relevant ({self.EXPLANATION_INPUT_LIMIT} word limit)."
            return [reply]

        if self.state == State.AWAITING_NUDITY_EXPLANATION_INPUT:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                self.reason.append('Something else: ' + message.content)
                self.state = State.AWAITING_MINOR_INVOLVEMENT_ANSWER
                reply = self.create_options_list("Does the abuse involve someone under 18, either you or someone else?",
                                                 self.YES_NO_OPTIONS)
            return [reply]

        if self.state == State.AWAITING_FINAL_ADDITIONAL_INFORMATION:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                self.reason.append('Additional information: ' + message.content)
                self.state = State.AWAITING_BLOCK_ANSWER
                reply = [self.REPORT_COMPLETE_SEXTORTION_MESSAGE,
                         self.create_options_list("Would you like to block this account?",
                                                  self.YES_NO_OPTIONS)]
            return reply

        if self.state == State.AWAITING_BLOCK_ANSWER:
            reply = ""
            i = self.get_index(message, self.YES_NO_OPTIONS)
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: yes, block account
                self.reason.append('Blocked user: ' + self.YES_NO_OPTIONS[i])
                reply = "The account you've reported will be blocked. "
                pass
            self.state = State.REPORT_COMPLETE
            reply += "Report complete."
            await self.submit_report()
            return [reply]

        return reply
    
    def create_options_list(self, prompt, options):
        res = prompt
        for i, option in enumerate(options):
            res += f"\n\t{i + 1}\. {option}"
        return res

    def get_index(self, message, options):
        try:
            i = int(message.content.strip())
            i -= 1
        except:
            return -1
        if i not in range(len(options)):
            return -1
        return i

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE