from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_INITIAL_REASON = auto()
    AWAITING_NUDITY_REASON = auto()
    AWAITING_HARASSMENT_REASON = auto()
    AWAITING_MINOR_REASON = auto()
    AWAITING_ASKED_FOR_MONEY_ANSWER = auto()
    AWAITING_MET_IN_PERSON_ANSWER = auto()
    AWAITING_BLACKMAIL_REASON = auto()
    AWAITING_EXPLANATION_INPUT = auto()
    AWAITING_MINOR_EXPLANATION_INPUT = auto()
    REPORT_COMPLETE = auto()

class ModeratorState(Enum):
    AWAITING_DECISION = auto()
    AWAITING_ACTION = auto()
    ACTION_COMPLETE = auto()

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
        "Nudity or Sexual Activity",
        "Bullying or Harassment",
        "Other Abuse"
    ]
    NUDITY_OPTIONS = [
        "Involves someone under 18",
        "Nudity or Pornography",
        "Sexual Exploitation or Solicitation",
        "Threat to share or has shared images",
        "Something else"
    ]
    MINOR_OPTIONS = [
        "They sent me intimate images of themselves or of someone else",
        "They are threatening to share intimate pictures of me",
        "They asked for intimate images of me",
        "Something else"
    ]
    HARASSMENT_OPTIONS = [
        "Hate Speech or other",
        "Blackmail"
    ]
    BLACKMAIL_OPTIONS = [
        "Nudity or Sexual Activity",
        "Other"
    ]

    REPORT_COMPLETE_OTHER_MESSAGE = "Thank you for helping us keep our community safe! We will investigate the matter and follow up as needed."
    REPORT_COMPLETE_SEXTORTION_MESSAGE = '''Thank you for helping us keep our community safe! We will investigate the matter and follow up as needed.
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
                print("Sending feedback to user.")
                print('User ID:', self.user_id)
                print('User:', self.user)
                print('Message Link:', self.message_link)
                print('Message:', self.message)
                print('Reason:', self.reason)
                await self.user.send("Report cannot be submitted as some information is missing.")
            else:
                print("User object not set, cannot send feedback.")
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
            
            await mod_channel.send(report_message)
            await self.user.send("Our moderators will review your report and take appropriate action.")
        else:
            await self.user.send("Sorry, an error occurred while submitting your report. Please try again later or contact a moderator directly.")

    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
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
                reply = self.create_options_list("What best describes the issue?",
                                                  self.NUDITY_OPTIONS)
            elif i == 1:
                self.state = State.AWAITING_HARASSMENT_REASON
                reply = self.create_options_list("What best describes the issue?",
                                                  self.HARASSMENT_OPTIONS)
            else:
                self.state = State.REPORT_COMPLETE
                reply = self.REPORT_COMPLETE_OTHER_MESSAGE
                await self.submit_report()
                
            return [reply]
        
        if self.state == State.AWAITING_NUDITY_REASON:
            i = self.get_index(message, self.NUDITY_OPTIONS)
            self.reason.append(self.NUDITY_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                self.state = State.AWAITING_MINOR_REASON
                reply = self.create_options_list("What best describes the issue?",
                                                  self.MINOR_OPTIONS)
            elif i == 4:
                self.state = State.AWAITING_EXPLANATION_INPUT
                reply = f"Please tell us what happened in {self.EXPLANATION_INPUT_LIMIT} words or less."
            else:
                self.state = State.REPORT_COMPLETE
                reply = self.REPORT_COMPLETE_OTHER_MESSAGE
                await self.submit_report()
            return [reply]
        
        if self.state == State.AWAITING_MINOR_REASON:
            i = self.get_index(message, self.MINOR_OPTIONS)
            self.reason.append(self.MINOR_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                self.state = State.AWAITING_ASKED_FOR_MONEY_ANSWER
                reply = self.create_options_list("Did they ask for money?",
                                                  self.YES_NO_OPTIONS)
            elif i == 3:
                self.state = State.AWAITING_MINOR_EXPLANATION_INPUT
                reply = f"Please tell us what happened in {self.EXPLANATION_INPUT_LIMIT} words or less."
            else:
                self.state = State.AWAITING_MET_IN_PERSON_ANSWER
                reply = self.create_options_list("Have you met them in person?",
                                                  self.YES_NO_OPTIONS)
            return [reply]
        
        if self.state == State.AWAITING_ASKED_FOR_MONEY_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            self.reason.append('Asked for money:', self.YES_NO_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: handle yes
                pass
            if i == 1:
                # TODO: handle no
                pass
            self.state = State.AWAITING_MET_IN_PERSON_ANSWER
            reply = self.create_options_list("Have you or the person you are reporting on behalf met them in person?",
                                              self.YES_NO_OPTIONS)
            return [reply]
        
        if self.state == State.AWAITING_MET_IN_PERSON_ANSWER:
            i = self.get_index(message, self.YES_NO_OPTIONS)
            self.reason.append('Met in person:', self.YES_NO_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: handle yes, give highest priority
                pass
            if i == 1:
                # TODO: handle no
                pass
            self.state = State.REPORT_COMPLETE
            reply = self.REPORT_COMPLETE_SEXTORTION_MESSAGE
            await self.submit_report()
            return [reply]
        
        if self.state == State.AWAITING_HARASSMENT_REASON:
            i = self.get_index(message, self.HARASSMENT_OPTIONS)
            self.reason.append(self.HARASSMENT_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                # TODO: handle hate speech / other
                self.state = State.REPORT_COMPLETE
                reply = self.REPORT_COMPLETE_OTHER_MESSAGE
                await self.submit_report()
            if i == 1: # blackmail, potentially sextortion
                self.state = State.AWAITING_BLACKMAIL_REASON
                reply= self.create_options_list("What best describes the issue?",
                                                  self.BLACKMAIL_OPTIONS)
            return [reply]
        
        if self.state == State.AWAITING_BLACKMAIL_REASON:
            i = self.get_index(message, self.BLACKMAIL_OPTIONS)
            self.reason.append(self.BLACKMAIL_OPTIONS[i])
            if i == -1:
                return ["Please enter a number corresponding to the given options."]
            if i == 0:
                self.state = State.AWAITING_NUDITY_REASON
                reply = self.create_options_list("What best describes the issue?",
                                                 self.NUDITY_OPTIONS)
            if i == 1:
                self.state = State.REPORT_COMPLETE
                reply = self.REPORT_COMPLETE_OTHER_MESSAGE
                await self.submit_report()
            return [reply]
        
        if self.state == State.AWAITING_EXPLANATION_INPUT:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                # TODO: forward explantation to moderator?
                reply = self.REPORT_COMPLETE_OTHER_MESSAGE
                self.state = State.REPORT_COMPLETE
                await self.submit_report()
            return [reply]
        
        if self.state == State.AWAITING_MINOR_EXPLANATION_INPUT:
            if len(message.content.split()) > self.EXPLANATION_INPUT_LIMIT:
                reply = f"Please do not exceed the {self.EXPLANATION_INPUT_LIMIT} word limit."
            else:
                # TODO: forward explantation to moderator?
                self.state = State.AWAITING_MET_IN_PERSON_ANSWER
                reply = self.create_options_list("Have you or the person you are reporting on behalf met them in person?",
                                            self.YES_NO_OPTIONS)
            return [reply]

        return []
    
    def create_options_list(self, prompt, options):
        res = prompt
        for i, option in enumerate(options):
            res += f"\n\t{i}\. {option}"
        return res
    
    def get_index(self, message, options):
        try:
            i = int(message.content.strip())
        except:
            return -1
        if i not in range(len(options)):
            return -1
        return i

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
class ModeratorReport:
    def __init__(self, client, message):
        self.client = client
        self.original_message = message
        self.state = ModeratorState.AWAITING_DECISION
        self.reported_user_id = None
        self.reported_user_name = None
        self.extract_reported_user_info()

    def extract_reported_user_info(self):
        lines = self.original_message.content.split('\n')
        for line in lines:
            if line.startswith("**Reported User:**"):
                match = re.search(r'<@(\d+)>', line)
                if match:
                    self.reported_user_id = int(match.group(1))
                match = re.search(r'\((.+?)\)', line)
                if match:
                    self.reported_user_name = match.group(1)
                break

    async def handle_message(self, message):
        if self.state == ModeratorState.AWAITING_ACTION:
            print("Handling moderator message..")
            if message.content.startswith("!ban"):
                await self.handle_ban(message)
            elif message.content.startswith("!hide"):
                await self.handle_hide_profile(message)
            elif message.content.startswith("!escalate"):
                await self.handle_escalate(message)
            else:
                await message.channel.send("Please enter a valid command: `ban`, `hide`, or `escalate`.")

    async def handle_ban(self, message):
        print("Handling ban command...")
        print("Reported User ID:", self.reported_user_id)
        if self.reported_user_id:
            try:
                user = await self.client.fetch_user(self.reported_user_id)
                await message.channel.send(f"User {self.reported_user_name} has been banned.")
            except discord.NotFound:
                await message.channel.send("User not found.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")
        else:
            await message.channel.send("Reported user information not found.")

    async def handle_hide_profile(self, message):
        if self.reported_user_id:
            await message.channel.send(f"Profile for user {self.reported_user_name} has been hidden (simulated).")
        else:
            await message.channel.send("Reported user information not found.")

    async def handle_escalate(self, message):
        await message.channel.send("Report has been escalated to higher authorities (simulated).")

    def report_complete(self):
        return self.state == ModeratorState.ACTION_COMPLETE