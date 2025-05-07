from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    IN_REPORTING_FLOW = auto()
    REPORT_COMPLETE = auto()
    PSEUDO_BAN_USER = auto()
    REMOVE_MESSAGE = auto()
    ADDING_INFO = auto()

user_flow_config = {
    "why_report": {
        "message": """Why are you reporting this post?\n"""
                   """1. I just don't like it\n"""
                   """2. Bullying or unwanted contact\n"""
                   """3. Suicide, self-injury, or eating disorders\n"""
                   """4. Violence, hate, or exploitation\n"""
                   """5. Selling or promoting restricted items\n"""
                   """6. Nudity or sexual activity\n"""
                   """7. Scam, fraud, or spam\n"""
                   """8. False information\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_no_report"),
            ("2", "how_bullying"),
            ("3", "what_self_harm"),
            ("4", "how_violence"),
            ("5", "what_sold"),
            ("6", "how_nudity"),
            ("7", "which_best_fraud_scam"),
            ("8", "thanks_for_your_feedback_with_report"),
        ],
    },
    "thanks_for_your_feedback_no_report": {
        "message": """**Thanks for your feedback**\n"""
                   """When you see something\n"""
                   """that you don't like on\n"""
                   """Instagram, you can report\n"""
                   """it if it doesn't follow our\n"""
                   """Community Standards or\n"""
                   """you can remove the\n"""
                   """person who shared it from\n"""
                   """your experience.\n""",
    },
    "how_bullying": {
        "message": """How is it bullying or unwanted contact?\n"""
                   """1. Threatening to share or sharing nude images\n"""
                   """2. Bullying or harassment\n"""
                   """3. Spam\n""",
        "choices": [
            ("1", "under_18"),
            ("2", "who_harassed"),
            ("3", "thanks_for_your_feedback_with_report"),
        ]
    },
    "how_violence": {
        "message": """How is it hate, violence, or exploitation?\n"""
                   """1. Seems like exploitation\n"""
                   """2. Calling for violence\n"""
                   """3. Hate speech or symbols\n"""
                   """4. Showing violence, death, or severe injury\n"""
                   """5. Seems like terrorism or organised crime\n"""
                   """6. Animal abuse\n"""
                   """7. Credible threat to safety\n""",
        "choices": [
            ("1", "what_expoloitation"),
            ("2", "thanks_for_your_feedback_with_report"),
            ("3", "thanks_for_your_feedback_with_report"),
            ("4", "thanks_for_your_feedback_with_report"),
            ("5", "thanks_for_your_feedback_with_report"),
            ("6", "thanks_for_your_feedback_with_report"),
            ("7", "thanks_for_your_feedback_with_report"),
        ]
    },
    "what_sold": {
        "message": """What is being sold or promoted?\n"""
                   """1. Drugs\n"""
                   """2. Weapons\n"""
                   """3. Animals\n""",
        "choices": [
            ("1", "what_drugs"),
            ("2", "thanks_for_your_feedback_with_report"),
            ("3", "thanks_for_your_feedback_with_report"),
        ]
    },
    "how_nudity": {
        "message": """How is this nudity or sexual activity.\n"""
                   """1. Threatening to share or sharing nude images\n"""
                   """2. Seems like prostitution\n"""
                   """3. Seems like sexual exploitation\n"""
                   """4. Nudity or sexual activity\n""",
        "choices": [
            ("1", "under_18"),
            ("2", "thanks_for_your_feedback_with_report"),
            ("3", "content_involve_someone_under_18"),
            ("4", "thanks_for_your_feedback_with_report"),
        ]
    },
    "which_best_fraud_scam": {
        "message": """Which bests describes the problem.\n"""
                   """1. Fraud or scam\n"""
                   """2. Spam\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "thanks_for_your_feedback_with_report"),
        ]
    },
    "under_18": {
        "message": """Are you under 18?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "thanks_for_your_feedback_with_report"),
        ]
    },
    "who_harassed": {
        "message": """Who is being harassed?\n"""
                   """1. Me\n"""
                   """2. A friend\n"""
                   """3. I don't know them\n""",
        "choices": [
            ("1", "under_18"),
            ("2", "involve_someone_under_18"),
            ("3", "involve_someone_under_18"),
        ]
    },
    "what_self_harm": {
        "message": """What kind of self-harm?\n"""
                   """1. Suicide or self-injury\n"""
                   """2. Eating disorder\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "thanks_for_your_feedback_with_report"),
        ]
    },
    "what_exploitation": {
        "message": """What kind of exploitation?\n"""
                   """1. Human trafficking\n"""
                   """2. Seems like sexual exploitation\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "content_involve_someone_under_18"),
        ]
    },
    "what_drugs": {
        "message": """What kind of drugs?\n"""
                   """1. Highly addictive drugs such as cocaine, heroin, or fentanyl\n"""
                   """2. Prescription medicine\n"""
                   """3. Other drugs\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "thanks_for_your_feedback_with_report"),
            ("3", "thanks_for_your_feedback_with_report"),
        ]
    },
    "involve_someone_under_18": {
        "message": """Does it involve someone who appears to be under the age of 18?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "thanks_for_your_feedback_with_report"),
        ]
    },
    "content_involve_someone_under_18": {
        "message": """Does this content involve someone who appears to be under the age of 18?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "thanks_for_your_feedback_with_report"),
            ("2", "thanks_for_your_feedback_with_report"),
        ]
    },
    "thanks_for_your_feedback_with_report": {
        "message": """**Thanks for reporting this post.**\n"""
                   """You'll get a notification once we've reviewedyour report.\n"""
                   """Thanks for helping us keep Instagram a safe and supportive community."""
    }
}

class ReportingFlow:
    def __init__(self, config, start_state):
        self.config = config
        self.state = start_state
    
    def transition_state(self, message):
        for match, transition in self.config[self.state]["choices"]:
            if message.strip() == match:
                self.state = transition
                return True
        return False
    
    def get_current_message(self):
        return self.config[self.state]["message"]

    def in_terminal_state(self):
        return self.config[self.state].get("choices") is None
    
class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.target_message = None
        self.reporting_flow = ReportingFlow(config=user_flow_config, start_state="why_report")
        
    
    async def remove_message(self):
        try:
            await self.target_message.delete()
            self.state = State.REPORT_COMPLETE
            return ["```" + self.target_message.author.name + ": " + self.target_message.content + "```" + " is now removed"]
        except discord.Forbidden:
            return ["❌ I lack permissions to delete that message."]

    def pseudo_ban_user(self):
        return [f"User: {self.target_message.author.name} banned for message {self.target_message.content}."]

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report completed."]
        
        elif self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        elif self.state == State.AWAITING_MESSAGE:
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
                self.target_message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            self.state = State.IN_REPORTING_FLOW
            
            return [
                "I found this message:", "```"
                + message.author.name + ": "
                + message.content
                + "```" + "\n"
                + self.reporting_flow.get_current_message()]
        elif self.state == State.IN_REPORTING_FLOW:
            if self.reporting_flow.transition_state(message.content):
                if self.reporting_flow.in_terminal_state():
                    self.state = State.REPORT_COMPLETE
                return [
                    self.reporting_flow.get_current_message()
                ]
            # For invalid choices
            else:
                return [
                    f"""Your choice {message.content} did not match any of the possible choices.\n"""
                    """Please select one of the numbers matching a choice below for the following question.\n"""
                    """Type only the number and nothing else.\n"""
                    + self.reporting_flow.get_current_message()
                ]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE