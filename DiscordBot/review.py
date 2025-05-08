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

review_flow_config = {
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
            ("1", "remove_post_warn_user"),
            ("2", "remove_post_warn_user"),
            ("3", "remove_post_warn_user_high"),
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
        "message": """What platform policy does the content violate?\n"""
                   """1. Bullying or unwanted contact\n"""
                   """2. Suicide, self-injury, or eating disorders\n"""
                   """3. Selling or promoting restricted items\n"""
                   """4. Nudity or sexual activity\n"""
                   """5. Spam, fraud, or scam\n"""
                   """6. False Information""",
        "choices": [
            ("1", "remove_post"),
            ("2", "remove_post"),
            ("3", "remove_post"),
            ("4", "remove_post"),
            ("5", "remove_post"),
            ("6", "remove_post"),
        ]
    },
    "reported_with_bad_intent": {
        "message": """Does this message appear to have reported the message with harmful intent?\n"""
                   """1. Yes\n"""
                   """2. No\n""",
        "choices": [
            ("1", "warn_reporting_user"),
            ("2", "thanks_feedback_low"),
        ]
    },
    "warn_reporting_user": {
        "message": """**Thanks for reviewing this post.**\n"""
                   """The reporting user will be sent a warning \n"""
                   """Thanks for helping us keep Instagram a safe and supportive community.""",
    },
    "thanks_feedback_low":{
        "message": """Thanks for reviewing this post.\n"""
                     """We will continue to monitor this account for guideline violations.\n"""
                   """The necessary action will be taken to ensure community safety.\n"""
    },

    "remove_post_warn_user":{
        "message": """Thanks for reviewing this post\n"""
                     """The post will be removed and the user will receive a direct message warning\n"""
                   
    },

    "remove_post_warn_user_high":{
        "message": """Thanks for reviewing this post\n"""
                     """The post will be removed and the user will receive a direct message warning\n"""
                     """Additionaly, the account will be reviewed for suspension"""
                   
    },

    "remove_post":{
        "message": """Thanks for reviewing this post\n"""
                     """The user's post will be removed\n"""
                   
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
        self.target_report = None
        self.review_flow = ReviewFlow(config=review_flow_config, start_state="initial_review")
    
    async def remove_message(self):
        try:
            await self.target_report.target_message.delete()
            self.state = State.REVIEW_COMPLETE
            return ["```" + self.target_report.target_message.author.name + ": " + self.target_report.target_message.content + "```" + " is now removed"]
        except discord.Forbidden:
            return ["❌ I lack permissions to delete that message."]

    async def warn_user(self, reporting):
        try:
            user = None
            if reporting:
                user = self.target_report.reporting_user
            else:
                user = self.target_report.target_message.author
            warning_message = (
                "⚠️ **Warning**\n"
                "Your recent message has been flagged for review and was found to violate our community guidelines. "
                "Please adhere to the platform rules to avoid further action."
            )
            await user.send(warning_message)
            self.state = State.REVIEW_COMPLETE
            return [f"✅ Warning sent to {user.name}."]
        except discord.Forbidden:
            return ["❌ Could not send warning DM — the user may have DMs disabled or blocked the bot."]
        except Exception as e:
            return [f"❌ Failed to send warning due to an error: {str(e)}"]

    
    def pseudo_ban_user(self):
        return [f"User: {self.target_report.target_message.author.name} banned for message {self.target_report.target_message.content}."]

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
            reply += "Please copy paste the link to the message from the mod channel you want to review.\n"
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
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            report = self.client.reports_to_review[int(m.group(3))]

            self.state = State.IN_REVIEW_FLOW
            self.target_report = report
            return [
                "I found this message:", "```"
                + report.target_message.author.name + ": "
                + report.target_message.content
                + "```" + "\n"
                + self.review_flow.get_current_message()]
        elif self.state == State.IN_REVIEW_FLOW:
            if self.review_flow.transition_state(message.content):
                if self.review_flow.state == "remove_post_warn_user" or self.review_flow.state == "remove_post_warn_user_high":
                    remove_result = await self.remove_message()
                    warn_result = await self.warn_user(False)
                    to_return = remove_result + warn_result 
                    if self.review_flow.state == "remove_post_warn_user":
                        return to_return
                    else:
                        return to_return + ["Additionally, the content will be reviewed by a team of specialists to decide whether the account will be banned."]

                
                elif self.review_flow.state == "remove_post":
                    remove_result = await self.remove_message()
                    return remove_result
                
                elif self.review_flow.state == "warn_reporting_user":
                    warn_result = await self.warn_user(True)
                    return warn_result
        
                if self.review_flow.in_terminal_state():
                    self.state = State.REVIEW_COMPLETE
                    self.client.manual_reviews.pop(message.author.id)
                    self.client.reports_to_review.pop(message.id)
                
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
        else:
            return ["You must finish a review before starting a new one"]
    
    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE