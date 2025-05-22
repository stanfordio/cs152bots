from enum import Enum, auto
import discord
import re
import asyncio


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    TYPE_SELECTED = auto()
    SUBTYPE_SELECTED = auto()
    AWAITING_Q1 = auto()
    AWAITING_Q2 = auto()
    AWAITING_BLOCK_CONFIRMATION = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    CATEGORIES = {
        "harassment": ["bullying", "hate speech", "stalking", "doxxing"],
        "fraud": ["phishing", "investment", "impersonation", "malware"],
        "inappropriate content": ["sexual - adult", "sexual - minor", "violence"],
        "disinformation": ["health", "legal", "political"],
        "spam": ["mass messaging", "bot messages", "off-topic flooding"],
        "immediate threat": ["suicidal intent", "self-harm intent", "violence towards others", "violence towards me"]
    }

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reported_message = None
        self.type_selected = None
        self.subtype_selected = None
        self.q1_response = None
        self.q2_response = None
        self.block_response = None
        self.author_id = None
        self.guild_id = None

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
            print(m)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                fetched_message = await channel.fetch_message(int(m.group(3)))
                self.message = fetched_message
                self.reported_message = fetched_message
                self.guild_id = guild.id
                print(self.reported_message)
                print(type(self.reported_message))
               
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            # Build numbered list of categories
            categories = list(self.CATEGORIES.keys())
            self.category_map = {str(i + 1): cat for i, cat in enumerate(categories)}  # e.g., "1": "harassment"
            numbered_list = "\n".join([f"{i + 1}. {cat}" for i, cat in enumerate(categories)])

            self.state = State.MESSAGE_IDENTIFIED
            return [
                "Thank you for taking the time to keep our community safe.",
                f"I found this message:",
                f"```{message.author.name}: {message.content}```",
                "Why are you reporting this post?\n" + numbered_list,
                "Please respond with the number of the category."
            ]


        if self.state == State.MESSAGE_IDENTIFIED:
            input_text = message.content.strip()
            if input_text in self.category_map:
                self.type_selected = self.category_map[input_text]
                self.state = State.TYPE_SELECTED
                subtypes = self.CATEGORIES[self.type_selected]
                self.subtype_map = {str(i+1): sub for i, sub in enumerate(subtypes)}
                numbered_options = "\n".join([f"{i+1}. {sub}" for i, sub in enumerate(subtypes)])
                return [
                    f"We're sorry that you're experiencing this kind of content on our platform. We'll do our best to help.",
                    f"What type of {self.type_selected} are you reporting?\n{numbered_options}",
                    "Please respond with the number of the option."
                ]
            else:
                return ["Please respond with a valid category number from the list."]


        
        if self.state == State.TYPE_SELECTED:
            input_text = message.content.strip()
            if input_text in self.subtype_map:
                self.subtype_selected = self.subtype_map[input_text]
                self.state = State.SUBTYPE_SELECTED
                return ["Thank you for reporting this post. Would you like to answer more questions that will help us resolve this more quickly? (yes/no)"]
            else:
                return ["Please respond with a valid number from the list."]

        
        if self.state == State.SUBTYPE_SELECTED:
            if message.content.lower() == "yes":
                self.state = State.AWAITING_Q1
                return ["Do you think this post was, in part or entirely, generated by AI? (yes/no)"]
            elif message.content.lower() == "no":
                return await self.ask_block_confirmation()
            else:
                return ["Please respond with `yes` or `no`."]
            
        if self.state == State.AWAITING_Q1:
            if message.content.lower() == "yes":
                self.q1_response = "yes"
                # if msg contains an image, ask q2. For now, only ask q1 and await block confirmation
                return await self.ask_block_confirmation()

            elif message.content.lower() == "no":
                self.q1_response = "no"
                # if msg contains an image, ask q2. For now, only ask q1 and await block confirmation
                return await self.ask_block_confirmation()
            else:
                return ["Please respond with `yes` or `no`."]
                    
        if self.state == State.AWAITING_BLOCK_CONFIRMATION:
            if message.content.lower() == "yes":
                self.block_response = "yes"
                return await self.report_complete("You will no longer see posts from this user in your feed.")
            elif message.content.lower() == "no":
                self.block_response = "no"
                return await self.report_complete("You will continue to see posts from this user in your feed. Thank you for your report.")
            else:
                return ["Please respond with `yes` or `no`."]
        
    async def ask_block_confirmation(self):
        self.state = State.AWAITING_BLOCK_CONFIRMATION
        return ["Thank you for reporting this post. Our team will review and take the necessary actions.", \
                "We may remove this post and/or remove the offender's account.", \
                "Would you like to block posts from this user in the future? This change would only be visible to you. (yes/no)"]
    

    async def report_complete(self, response):
        self.state = State.REPORT_COMPLETE
        return [response]
