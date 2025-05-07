from enum import Enum, auto
import discord
import re

class State(Enum):
    REVIEW_START = auto()
    AWAITING_MESSAGE = auto()
    IN_REVIEW_FLOW = auto()
    REVIEW_COMPLETE = auto()
    PSEUDO_BAN_USER = auto()
    REMOVE_MESSAGE = auto()
    ADDING_INFO = auto()

user_flow_config = {
    "initial_review": {
        "message": """Does the post violate the platform's guidelines on hate speech?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "rank_intensity"),
            ("2", "violate_other_policies"),
        ],
    },
    "rank_intensity": {
        "message": """Please rank the intensity of the hate speech\n"""
                   """1. Low Intensity\n"""
                   """2. Medium Intensity\n"""
                   """3. High Intensity\n""",
        "choices": [
            ("1", "thanks_feedback_low"),
            ("2", "thanks_feeback_low"),
            ("3", "thanks_feedback_high"),
        ]
    },
    "violate_other_policies": {
        "message": """Does this content violate other platform policies?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "violate_what_policies"),
            ("2", "reported_with_bad_intent"),
            
        ]
    },
    "violate_what_policies": {
        "message": """What platform policy does the conent violate?\n"""
                   """1. Bullying or unwanted contact\n"""
                   """2. Suicide, self-injury, or eating disorders\n"""
                   """3. Selling or promoting restricted items\n""",
                   """4. Nudity or sexual activity\n"""
                   """5. Spam, fraud, or scam\n"""
                   """6. False Information"""
        "choices": [
            ("1", "thanks_feedback_low"),
            ("2", "thanks_feedback_low"),
            ("3", "thanks_feedback_low"),
            ("4", "thanks_feedback_low"),
            ("5", "thanks_feedback_low"),
            ("6", "thanks_feedback_low"),
        ]
    },
    "reported_with_bad_intent": {
        "message": """Does this message appear to have reported the message with harmful intent?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "thanks_feedback_low"),
            ("2", "thanks_feedback_high"),
        ]
    },
    "thanks_feedback_high": {
        "message": """**Thanks for reviewing this post.**\n"""
                   """This post will be further reviewed by our team of specialists.\n"""
                   """Thanks for helping us keep Instagram a safe and supportive community.""",
    },
    "thanks_feedback_low":{
        "message": """Thanks for reviewing this post.]\n"""
                     """We will continue to monitor this account for guideline violations\n"""
                   """The necessary action will be taken to ensure community safety.\n"""
    }
}

class ReviewFlow:
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
    
class Review:
    START_KEYWORD = "review"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.target_message = None
        self.review_flow = ReviewFlow(config=user_flow_config, start_state="initial_review")
    
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
        This function makes up the meat of the manual review flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REVIEW_COMPLETE
            return ["Review completed."]
        
        elif self.state == State.REVIEW_START:
            reply =  "Thank you for starting the review process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy the exact username of the **reporting** user.\n"
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        elif self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            username = message.content.strip()
            if username not in self.client.name_to_id or self.client.name_to_id[username] not in self.client.reports:
                return ["I'm sorry, there is no known report for this username. Please try again or say 'cancel' to cancel."]


            report = self.client.reports[self.client.name_to_id[username]]
            if report.target_message is None:
                return ["The reported message has not been set yet. Please ensure the user completed the report."]

            self.state = State.IN_REVIEW_FLOW
            return [
                "I found this message:", "```"
                + report.target_message.author.name + ": "
                + report.target_message.content
                + "```" + "\n"
                + self.review_flow.get_current_message()]
        elif self.state == State.IN_REVIEW_FLOW:
            if self.review_flow.transition_state(message.content):
                if self.review_flow.in_terminal_state():
                    self.state = State.REVIEW_COMPLETE
                return [
                    self.review_flow.get_current_message()
                ]
            # For invalid choices
            else:
                return [
                    f"""Your choice {message.content} did not match any of the possible choices.\n"""
                    """Please select one of the numbers matching a choice below for the following question.\n"""
                    """Type only the number and nothing else.\n"""
                    + self.review_flow.get_current_message()
                ]

    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE