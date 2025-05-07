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
            reply += "• BULLYING\n"
            reply += "• SUICIDE/SELF-HARM\n"
            reply += "• SEXUALLY EXPLICIT/NUDITY\n"
            reply += "• MISINFORMATION\n"
            reply += "• HATE SPEECH\n"
            reply += "• DANGER"
            return ["I found this message:", "```" + self.message.author.name + ": " + self.message.content + "```", reply]

        if self.state == State.AWAITING_ABUSE_TYPE:
            abuse_type = message.content.lower()
            if abuse_type in SUICIDE_VARIANTS:
                self.abuse_type = AbuseType.SUICIDE
                mod_channel = self.client.mod_channels[self.message.guild.id]
                await mod_channel.send(f"🔴 URGENT - SUICIDE/SELF-HARM REPORT:\n{self.message.author.name}: {self.message.content}")
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting. This has been escalated to our moderation team for immediate review."]

            if abuse_type in EXPLICIT_VARIANTS:
                self.abuse_type = AbuseType.EXPLICIT
                mod_channel = self.client.mod_channels[self.message.guild.id]
                await mod_channel.send(f"🔴 URGENT - EXPLICIT CONTENT REPORT:\n{self.message.author.name}: {self.message.content}")
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting. This has been escalated to our moderation team for immediate review."]

            for type in AbuseType:
                if abuse_type == type.value:
                    self.abuse_type = type
                    if type == AbuseType.MISINFORMATION:
                        self.state = State.AWAITING_MISINFO_CATEGORY
                        return ["Please select the misinformation category:\n• HEALTH\n• ADVERTISEMENT\n• NEWS"]
                    else:
                        mod_channel = self.client.mod_channels[self.message.guild.id]
                        priority = "🔴" if type in [AbuseType.HATE, AbuseType.DANGER] else "🟡"
                        await mod_channel.send(f"{priority} New report - {type.value.upper()}:\n{self.message.author.name}: {self.message.content}")
                        self.state = State.REPORT_COMPLETE
                        return ["Thank you for reporting, it has been sent to our moderation team."]
            return ["Please select a valid abuse type from the list above."]

        if self.state == State.AWAITING_MISINFO_CATEGORY:
            category = message.content.lower()
            for cat in MisinfoCategory:
                if category == cat.value:
                    self.misinfo_category = cat
                    if cat == MisinfoCategory.HEALTH:
                        self.state = State.AWAITING_HEALTH_CATEGORY
                        return ["Please specify the health misinformation category:\n• EMERGENCY\n• MEDICAL RESEARCH\n• REPRODUCTIVE HEALTHCARE\n• TREATMENTS\n• ALTERNATIVE MEDICINE"]
                    elif cat == MisinfoCategory.NEWS:
                        self.state = State.AWAITING_NEWS_CATEGORY
                        return ["Please specify the news category:\n• HISTORICAL\n• POLITICAL\n• SCIENCE"]
                    else:  # Advertisement
                        self.state = State.REPORT_COMPLETE
                        await self.client.mod_channels[self.message.guild.id].send(f"🟡 ADVERTISING MISINFO:\n{self.message.author.name}: {self.message.content}")
                        return ["This has been reported to our ad team."]
            return ["Please select a valid misinformation category from the list above."]

        if self.state == State.AWAITING_HEALTH_CATEGORY:
            health_cat = message.content.lower()
            for cat in HealthCategory:
                if health_cat == cat.value:
                    self.specific_category = cat
                    self.state = State.REPORT_COMPLETE
                    mod_channel = self.client.mod_channels[self.message.guild.id]
                    
                    if cat == HealthCategory.EMERGENCY:
                        await mod_channel.send(f"🔴 HEALTH MISINFO:\n{self.message.author.name}: {self.message.content}")
                        return ["We will prioritize this and send it for review."]
                    elif cat in [HealthCategory.MEDICAL_RESEARCH, HealthCategory.REPRODUCTIVE]:
                        await mod_channel.send(f"🟡 HEALTH MISINFO:\n{self.message.author.name}: {self.message.content}")
                        return ["This has been sent to moderators."]
                    else: 
                        await mod_channel.send(f"🟢 HEALTH MISINFO:\n{self.message.author.name}: {self.message.content}")
                        return ["This has been sent to our team. Review if necessary, marked with non-scientific flag."]
            return ["Please select a valid health category from the list above."]

        if self.state == State.AWAITING_NEWS_CATEGORY:
            news_cat = message.content.lower()
            for cat in NewsCategory:
                if news_cat == cat.value:
                    self.specific_category = cat
                    self.state = State.REPORT_COMPLETE
                    mod_channel = self.client.mod_channels[self.message.guild.id]
                    
                    if cat == NewsCategory.POLITICAL:
                        await mod_channel.send(f"🟡 NEWS MISINFO:\n{self.message.author.name}: {self.message.content}")
                    else:
                        await mod_channel.send(f"🟢 NEWS MISINFO:\n{self.message.author.name}: {self.message.content}")
                    return ["This has been sent to our team."]
            return ["Please select a valid news category from the list above."]

        return []

    def report_complete(self):
        """Returns whether the current report is in a completed state"""
        return self.state == State.REPORT_COMPLETE