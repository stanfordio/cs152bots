from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_ABUSE_TYPE = auto()
    AWAITING_MISINFO_CATEGORY = auto()
    AWAITING_HEALTH_CATEGORY = auto()
    AWAITING_NEWS_CATEGORY = auto()
    REPORT_COMPLETE = auto()
    AWAITING_APPEAL = auto()
    APPEAL_REVIEW = auto()

class AbuseType(Enum):
    BULLYING = "bullying"
    SUICIDE = "suicide/self-harm" 
    EXPLICIT = "sexually explicit/nudity"
    MISINFORMATION = "misinformation"
    HATE = "hate speech"
    DANGER = "danger"

SUICIDE_VARIANTS = {
    "suicide", 
    "self harm", 
    "self-harm",
    "selfharm",
    "suicide/self harm",
    "suicide/selfharm",
    "suicide/self-harm",
}

EXPLICIT_VARIANTS = {
    "explicit",
    "sexually explicit",
    "sexual",
    "nudity",
    "nude",
    "sexually explicit/nudity",
}

class MisinfoCategory(Enum):
    HEALTH = "health"
    ADVERTISEMENT = "advertisement"
    NEWS = "news"

class HealthCategory(Enum):
    EMERGENCY = "emergency"
    MEDICAL_RESEARCH = "medical research"
    REPRODUCTIVE = "reproductive healthcare"
    TREATMENTS = "treatments"
    ALTERNATIVE = "alternative medicine"

class NewsCategory(Enum):
    HISTORICAL = "historical"
    POLITICAL = "political"
    SCIENCE = "science"

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuse_type = None
        self.misinfo_category = None
        self.specific_category = None

    async def handle_message(self, message):
        if message.content.lower() == self.CANCEL_KEYWORD:
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
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            self.state = State.AWAITING_ABUSE_TYPE
            reply = "What type of abuse would you like to report?\n"
            reply += "1. BULLYING\n"
            reply += "2. SUICIDE/SELF-HARM\n"
            reply += "3. SEXUALLY EXPLICIT/NUDITY\n"
            reply += "4. MISINFORMATION\n"
            reply += "5. HATE SPEECH\n"
            reply += "6. DANGER"
            return ["I found this message:", "```" + self.message.author.name + ": " + self.message.content + "```", reply]

        if self.state == State.AWAITING_ABUSE_TYPE:
            abuse_type = message.content.strip()
            abuse_types = {
                '1': AbuseType.BULLYING,
                '2': AbuseType.SUICIDE,
                '3': AbuseType.EXPLICIT,
                '4': AbuseType.MISINFORMATION,
                '5': AbuseType.HATE,
                '6': AbuseType.DANGER
            }
            
            if abuse_type not in abuse_types:
                return ["Please select a valid option (1-6) from the list above."]
            
            self.abuse_type = abuse_types[abuse_type]
            
            if self.abuse_type == AbuseType.SUICIDE:
                mod_channel = self.client.mod_channels[self.message.guild.id]
                await mod_channel.send(f"SUICIDE/SELF-HARM REPORT:\n{self.message.author.name}: {self.message.content}")
                await self.client.start_moderation_flow(
                    report_type="SUICIDE/SELF-HARM",
                    report_content=self.message.content,
                    message_author=self.message.author.name
                )
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting. This has been sent to our moderation team for review."]

            if self.abuse_type == AbuseType.EXPLICIT:
                mod_channel = self.client.mod_channels[self.message.guild.id]
                await mod_channel.send(f"EXPLICIT CONTENT REPORT:\n{self.message.author.name}: {self.message.content}")
                await self.client.start_moderation_flow(
                    report_type="EXPLICIT CONTENT",
                    report_content=self.message.content,
                    message_author=self.message.author.name
                )
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting. This has been sent to our moderation team for review."]

            if self.abuse_type == AbuseType.MISINFORMATION:
                self.state = State.AWAITING_MISINFO_CATEGORY
                return ["Please select the misinformation category:\n1. HEALTH\n2. ADVERTISEMENT\n3. NEWS"]
            else:
                mod_channel = self.client.mod_channels[self.message.guild.id]
                await mod_channel.send(f"New report - {self.abuse_type.value.upper()}:\n{self.message.author.name}: {self.message.content}")
                await self.client.start_moderation_flow(
                    report_type=self.abuse_type.value.upper(),
                    report_content=self.message.content,
                    message_author=self.message.author.name
                )
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting, it has been sent to our moderation team."]

        if self.state == State.AWAITING_MISINFO_CATEGORY:
            category = message.content.strip()
            misinfo_categories = {
                '1': MisinfoCategory.HEALTH,
                '2': MisinfoCategory.ADVERTISEMENT,
                '3': MisinfoCategory.NEWS
            }
            
            if category not in misinfo_categories:
                return ["Please select a valid option (1-3) from the list above."]
            
            self.misinfo_category = misinfo_categories[category]
            
            if self.misinfo_category == MisinfoCategory.HEALTH:
                self.state = State.AWAITING_HEALTH_CATEGORY
                return ["Please specify the health misinformation category:\n1. EMERGENCY\n2. MEDICAL RESEARCH\n3. REPRODUCTIVE HEALTHCARE\n4. TREATMENTS\n5. ALTERNATIVE MEDICINE"]
            elif self.misinfo_category == MisinfoCategory.NEWS:
                self.state = State.AWAITING_NEWS_CATEGORY
                return ["Please specify the news category:\n1. HISTORICAL\n2. POLITICAL\n3. SCIENCE"]
            else:  # Advertisement
                self.state = State.REPORT_COMPLETE
                await self.client.mod_channels[self.message.guild.id].send(f"ADVERTISING MISINFO:\n{self.message.author.name}: {self.message.content}")
                await self.client.start_moderation_flow(
                    report_type="ADVERTISING MISINFO",
                    report_content=self.message.content,
                    message_author=self.message.author.name
                )
                return ["This has been reported to our ad team."]

        if self.state == State.AWAITING_HEALTH_CATEGORY:
            health_cat = message.content.strip()
            health_categories = {
                '1': HealthCategory.EMERGENCY,
                '2': HealthCategory.MEDICAL_RESEARCH,
                '3': HealthCategory.REPRODUCTIVE,
                '4': HealthCategory.TREATMENTS,
                '5': HealthCategory.ALTERNATIVE
            }
            
            if health_cat not in health_categories:
                return ["Please select a valid option (1-5) from the list above."]
            
            self.specific_category = health_categories[health_cat]
            self.state = State.REPORT_COMPLETE
            mod_channel = self.client.mod_channels[self.message.guild.id]
            await mod_channel.send(f"HEALTH MISINFO - {self.specific_category.value.upper()}:\n{self.message.author.name}: {self.message.content}")
            await self.client.start_moderation_flow(
                report_type=f"HEALTH MISINFO - {self.specific_category.value.upper()}",
                report_content=self.message.content,
                message_author=self.message.author.name
            )
            return ["This has been sent to our moderation team."]

        if self.state == State.AWAITING_NEWS_CATEGORY:
            news_cat = message.content.strip()
            news_categories = {
                '1': NewsCategory.HISTORICAL,
                '2': NewsCategory.POLITICAL,
                '3': NewsCategory.SCIENCE
            }
            
            if news_cat not in news_categories:
                return ["Please select a valid option (1-3) from the list above."]
            
            self.specific_category = news_categories[news_cat]
            self.state = State.REPORT_COMPLETE
            mod_channel = self.client.mod_channels[self.message.guild.id]
            await mod_channel.send(f"NEWS MISINFO - {self.specific_category.value.upper()}:\n{self.message.author.name}: {self.message.content}")
            await self.client.start_moderation_flow(
                report_type=f"NEWS MISINFO - {self.specific_category.value.upper()}",
                report_content=self.message.content,
                message_author=self.message.author.name
            )
            return ["This has been sent to our team."]

        return []

    async def notify_reported_user(self, user_name, guild, outcome, explanation=None):
        # Find the user object by name in the guild
        user = discord.utils.get(guild.members, name=user_name)
        if user:
            try:
                msg = f"Your message was reviewed by moderators. Outcome: {outcome}."
                if explanation:
                    msg += f"\nReason: {explanation}"
                msg += "\nIf you believe this was a mistake, you may reply to this message to appeal."
                await user.send(msg)
                if outcome == "Post removed.":
                    await self.notify_user_of_appeal_option(user_name, guild, explanation)
            except Exception as e:
                print(f"Failed to DM user {user_name}: {e}")

    def report_complete(self):
        """Returns whether the current report is in a completed state"""
        return self.state == State.REPORT_COMPLETE