from enum import Enum, auto
import discord
import re
from discord.components import SelectOption
from discord.ui import Select, View
from discord.ext import commands


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_ABUSE_TYPE = auto()
    AWAITING_SPECIFIC_ABUSE_TYPE = auto()
    IMMINENT_DANGER = auto()
    REMOVE_CONTENT = auto()
    AWAITING_DM_PERMISSION_REQUEST = auto()
    AWAITING_BLOCK_USER_REQUEST = auto()
    REPORT_COMPLETE = auto()


class BroadAbuseType(str, Enum):
    SPAM = "SPAM"
    EXPLICIT_CONTENT = 'EXPLICIT_CONTENT'
    THREAT = 'THREAT'
    HARASSMENT = "HARASSMENT"
    OTHER = 'OTHER'

    def __str__(self) -> str:
        return str.__str__(self)


class SpecificAbuseType(str, Enum):
    # BROAD: SPAM
    SCAM = "SCAM"
    BOTMESSAGES = "BOTMESSAGES"
    SOLICITATION = "SOLICITATION"
    IMPERSONATION = "IMPERSONATION"
    MISINFORMATION = "MISINFORMATION"

    # BROAD: EXPLICIT_CONTENT
    SEXUAL_CONTENT = "SEXUAL_CONTENT"
    VIOLENCE = "VIOLENCE"
    HATE_SPEECH = "HATE_SPEECH"

    # BROAD: THREAT
    SELF_HARM = "SELF_HARM"
    TERRORIST_PROPAGANDA = "TERRORIST_PROPAGANDA"
    DOXXING = "DOXXING"

    # BROAD: HARASSMENT
    BULLYING = "BULLYING"
    SEXUAL = "SEXUAL"
    CONTINUOUS_CONTACT = "CONTINUOUS_CONTACT"
    GROOMING = "GROOMING"

    def __str__(self) -> str:
        return str.__str__(self)


severities = {
    "Scam": 3,
    "Bot Messages": 2,
    "Soliciting": 2,
    "Impersonation": 3,
    "Misinformation": 2,
    "Sexual content": 3,
    "Violence": 4,
    "Hate Speech": 2,
    "Self harm / suicide": 4,
    "Credible threat of violence": 5,
    "Terrorist propaganda": 5,
    "Doxxing": 4,
    "Bullying": 3,
    "Sexually-related harassment": 4,
    "Hate Speech": 2,
    "Unsolicited continuous contact": 3,
    "Grooming": 5
},


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuse_type = None
        self.specific_abuse_type = None
        self.report_severity_multiplier = 1

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
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.AWAITING_ABUSE_TYPE
            return [{"text": "I found this message:"},
                    {"text": "```" + message.author.name +
                        ": " + message.content + "```"},
                    {"text": "Please select the reason for reporting this message.", "view": self.generate_abuse_type_menu()}]

        # If grooming has been selected, we need to collect more information
        if self.specific_abuse_type == SpecificAbuseType.GROOMING and self.state == State.IMMINENT_DANGER:
            self.state = State.AWAITING_DM_PERMISSION_REQUEST
            response = "Thank you for bringing this to our attention. \n"
            response += "Grooming is a serious issue and we need to collect more information to address it. \n"
            response += "Do you give us permission to review your message history with this person? (Yes/No)"
            return [response]

        # Need to know if the user gives permission to the bot to review their message history
        if self.state == State.AWAITING_DM_PERMISSION_REQUEST:
            self.state = State.AWAITING_BLOCK_USER_REQUEST
            response = ""
            if 'y' in message.content.lower():
                response += "Thank you for giving us permission to review your message history. \n"
                response += "Until the review process is complete, would you like to block this user? (Yes/No)"
            else:
                self.state = State.REPORT_COMPLETE
                response += "Our content moderation team will now review the reported message and take appropriate actions which may include removal of the messager's account. \n\n"
                response += "Thank you for contributing to the safety and quality of our platform!"

            return [response]

        # Need to know if the user wants to block the user who they reported
        if self.state == State.AWAITING_BLOCK_USER_REQUEST:
            response = ""
            self.state = State.REPORT_COMPLETE
            if 'y' in message.content.lower():
                # Block the user
                # TODO: Add in the username of the person whose message was reported
                response += "This person has now been blocked. If you would like to unblock them, you can do so in your message settings. \n\n"
            else:
                response += "This person will not be blocked. If change your mind and would like to block them, you can do so in your message settings. \n\n"
                response += "We always recommend that users be cautious when interacting with strangers online, and be wary of individuals who ask for personal information or request to meet in person. \n\n"
            response += "Thank you for contributing to the safety and quality of our platform!"
            return [response]

        # Once the user has selected abuse type and specific abuse type, and more information has been collected
        if self.state == State.IMMINENT_DANGER:
            self.state = State.REMOVE_CONTENT
            response = "Thank you for bringing this to our attention.\n"
            response += "Our team will review the reported content and take appropriate action against the content or account of the violator.\n"
            response += "Would you like us to remove the content from your feed? (Yes/No)"
            if 'y' in message.content.lower():
                self.report_severity_multiplier = 2
                # TODO: add in imminent danger message as needed.
            return [response]

        # We need to see if the user wants the content removed from their feed.
        if self.state == State.REMOVE_CONTENT:
            # TODO: Change this to something else so that report is not compelte until moderator reviews it?
            self.state = State.REPORT_COMPLETE
            response = ""
            if 'y' in message.content.lower():
                response += "The content has been removed from your feed. \n\n"
            response += "Thank you for contributing to the safety and quality of our platform!"
            return [response]

        #call compile message
        self.compile_report_to_moderate()

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def generate_abuse_type_menu(self):
        async def callback(interaction):
            self.abuse_type = select_menu.values[0]
            self.state = State.AWAITING_SPECIFIC_ABUSE_TYPE  # TODO: Check if needed?

            if self.abuse_type == BroadAbuseType.SPAM:
                await interaction.response.send_message(f"Please specify what kind of spam: ", view=self.generate_spam_type_menu())
            elif self.abuse_type == BroadAbuseType.EXPLICIT_CONTENT:
                await interaction.response.send_message(f"Please select the type of explicit content you've experienced: ", view=self.generate_explicit_content_type_menu())
            elif self.abuse_type == BroadAbuseType.THREAT:
                await interaction.response.send_message(f"Please select the type of threat you've experienced: ", view=self.generate_threat_type_menu())
            elif self.abuse_type == BroadAbuseType.HARASSMENT:
                await interaction.response.send_message(f"Please select the type of harassment you've experienced: ", view=self.generate_harassment_type_menu())
            else:
                self.state = State.IMMINENT_DANGER
                await interaction.response.send_message(f"Is there an immediate risk to someone's safety? (Yes/No)")

        choices = [
            SelectOption(
                label='Spam',
                description="Select this if you are receiving repetitive and unwanted messages.",
                value=BroadAbuseType.SPAM,
                emoji="📧"),
            SelectOption(
                label='Explicit Content',
                description="Select this for content that is sexually explicit or graphically violent.",
                value=BroadAbuseType.EXPLICIT_CONTENT,
                emoji="🔞"),
            SelectOption(
                label='Threat',
                description="Select this if there is a threat to oneself or others, including threats of violence.",
                value=BroadAbuseType.THREAT,
                emoji="⚠️"),
            SelectOption(
                label='Harassment',
                description="Select this for continuous aggressive pressure or intimidation.",
                value=BroadAbuseType.HARASSMENT,
                emoji="😠"),
            SelectOption(
                label='Other',
                description="Select this if you find the content uncomfortable or objectionable for other reasons.",
                value=BroadAbuseType.OTHER,
                emoji="❓"),
        ]

        select_menu = Select(
            placeholder='Why are you reporting this message?',
            options=choices,
            custom_id='report_reason_menu',
        )

        select_menu.callback = callback
        view = View()
        view.add_item(select_menu)
        return view

    def generate_spam_type_menu(self):
        async def callback(interaction):
            self.specific_abuse_type = select_menu.values[0]
            self.state = State.IMMINENT_DANGER
            response = f"You reported content for {self.specific_abuse_type}. Thank you for your feedback. \n"
            response += "Is there an immediate risk to someone's safety? (Yes/No)"
            await interaction.response.send_message(response)

        choices = [
            SelectOption(
                label='Scam',
                description="Content trying to deceitfully persuade you to give personal information or money.",
                value=SpecificAbuseType.SCAM,
                emoji="💸"
            ),
            SelectOption(
                label='Bot Messages',
                description="Bots sending unsolicited messages.",
                value=SpecificAbuseType.BOTMESSAGES,
                emoji="🤖"
            ),
            SelectOption(
                label='Solicitation',
                description="Unwanted direct solicitations for services or products.",
                value=SpecificAbuseType.SOLICITATION,
                emoji="📢"
            ),
            SelectOption(
                label='Impersonation',
                description="Someone is pretending to be someone else to deceive or mislead.",
                value=SpecificAbuseType.IMPERSONATION,
                emoji="🎭"
            ),
            SelectOption(
                label='Misinformation',
                description="Spreading false or misleading information.",
                value=SpecificAbuseType.MISINFORMATION,
                emoji="🗞️"
            ),
        ]

        select_menu = Select(
            placeholder='What specific type of spam are you reporting?',
            options=choices,
            custom_id='spam_type_menu',
        )

        select_menu.callback = callback
        view = View()
        view.add_item(select_menu)
        return view

    def generate_threat_type_menu(self):
        async def callback(interaction):
            self.specific_abuse_type = select_menu.values[0]

            self.state = State.IMMINENT_DANGER
            response = f"You reported a {self.specific_abuse_type} threat. Thank you for taking the time to report this issue. \n"
            response += "Is there an immediate risk to someone's safety? (Yes/No)"
            await interaction.response.send_message(response)

        choices = [
            SelectOption(
                label='Self Harm',
                description="Threat of self-inflicted harm or suicide.",
                value=SpecificAbuseType.SELF_HARM,
                emoji="🆘"
            ),
            SelectOption(
                label='Terrorist Propaganda',
                description="Content promotes terrorist activities or organizations.",
                value=SpecificAbuseType.TERRORIST_PROPAGANDA,
                emoji="💣"
            ),
            SelectOption(
                label='Doxxing',
                description="Someone's private information is being shared without consent.",
                value=SpecificAbuseType.DOXXING,
                emoji="🏴"
            ),
        ]

        select_menu = Select(
            placeholder='What specific type of threat are you reporting?',
            options=choices,
            custom_id='threat_type_menu',
        )

        select_menu.callback = callback
        view = View()
        view.add_item(select_menu)
        return view

    def generate_harassment_type_menu(self):
        async def callback(interaction):
            self.specific_abuse_type = select_menu.values[0]

            self.state = State.IMMINENT_DANGER
            response = f"You reported {self.specific_abuse_type} as the type of harassment. Thank you for informing us. \n"
            response += "Do you require immediate assistance? (Yes/No)"
            await interaction.response.send_message(response)

        choices = [
            SelectOption(
                label='Bullying',
                description="Repeated actions aimed at coercing someone unfairly.",
                value=SpecificAbuseType.BULLYING,
                emoji="👊"
            ),
            SelectOption(
                label='Sexual Harassment',
                description="Harassment of a sexual nature.",
                value=SpecificAbuseType.SEXUAL,
                emoji="🚫"
            ),
            SelectOption(
                label='Continuous Contact',
                description="Persistent and unwanted contact.",
                value=SpecificAbuseType.CONTINUOUS_CONTACT,
                emoji="📱"
            ),
            SelectOption(
                label='Grooming',
                description="Emotional connection to lower someone's inhibitions for abuse or exploitation.",
                value=SpecificAbuseType.GROOMING,
                emoji="🐺"
            ),
        ]

        select_menu = Select(
            placeholder='What specific type of harassment are you reporting?',
            options=choices,
            custom_id='harassment_type_menu',
        )

        select_menu.callback = callback
        view = View()
        view.add_item(select_menu)
        return view

    def generate_explicit_content_type_menu(self):
        async def callback(interaction):
            self.specific_abuse_type = select_menu.values[0]

            self.state = State.IMMINENT_DANGER
            response = f"You reported {self.specific_abuse_type}. Thank you for your feedback. \n"
            response += "Do you require immediate assistance? (Yes/No)"
            await interaction.response.send_message(response)

        choices = [
            SelectOption(
                label='Sexual Content',
                description="Sexual material or activity.",
                value=SpecificAbuseType.SEXUAL_CONTENT,
                emoji="🔞"
            ),
            SelectOption(
                label='Violence',
                description="Graphic depictions of violence.",
                value=SpecificAbuseType.VIOLENCE,
                emoji="⚔️"
            ),
            SelectOption(
                label='Hate Speech',
                description="Hate or violence against groups of specific identities.",
                value=SpecificAbuseType.HATE_SPEECH,
                emoji="🚫"
            ),
        ]

        select_menu = Select(
            placeholder='What type of explicit content are you reporting?',
            options=choices,
            custom_id='explicit_content_type_menu',
        )

        select_menu.callback = callback
        view = View()
        view.add_item(select_menu)
        return view

    def calculate_report_severity(self):
        return severities[self.specific_abuse_type] * self.report_severity_multiplier

    # TODO: Implement this method
    def compile_report_to_moderate(self):
        #add the info we want to self.state 
        return [{"text": "I found this message:"},
                    ]


        return

