from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    ''' Added the following 4 to facilitate more advanced state reception. '''
    AWAITING_CATEGORY = auto()  
    AWAITING_SUBCATEGORY = auto()
    AWAITING_SUBSUBCATEGORY = auto()
    AWAITING_CONFIRMATION = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    ''' Added the following to categorize abuse types. '''
    CATEGORIES = {
        "spam": ["fraud", "impersonation", "solicitation"],
        "offensive content": ["unwanted sexual content", "child sexual abuse content", "violence and gore", "non-consensual sharing of, or threats to share, intimate imagery", "terroristic content"],
        "harassment": ["bullying", "hate speech", "sexual harassment", "non-consensual sharing of, or threats to share, intimate imagery"],
        "imminent danger": {
            "self-harm and suicide": [],
            "threats": ["threatening violence", "glorifying violence", "publicizing private information", "non-consensual sharing of, or threats to share, intimate imagery"]
        }
    }

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
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
            self.state = State.MESSAGE_IDENTIFIED
        
        # modified - select top category
        if self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.AWAITING_CATEGORY
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please specify the category of the issue: " + ", ".join(self.CATEGORIES.keys())]

        # added - recieve top category
        if self.state == State.AWAITING_CATEGORY:
            self.category = message.content.lower()
            if self.category not in self.CATEGORIES:
                return ["Invalid category. Please specify one of the following: " + ", ".join(self.CATEGORIES.keys())]
            self.state = State.AWAITING_SUBCATEGORY
            if self.category == "imminent danger": # dif implementation because of nested subcategory
                return ["You've selected " + self.category + ". Please specify the subcategory: " + ", ".join(self.CATEGORIES[self.category].keys())]
            else:
                return ["You've selected " + self.category + ". Please specify the subcategory: " + ", ".join(self.CATEGORIES[self.category])]

        # added - recieve subcategory
        if self.state == State.AWAITING_SUBCATEGORY:
            self.subcategory = message.content.lower()
            if self.subcategory == "threats" and self.category == "imminent danger":
                self.state = State.AWAITING_SUBSUBCATEGORY
                return ["You've selected " + self.subcategory + ". Please specify the subcategory of 'Threats': " + ", ".join(self.CATEGORIES[self.category][self.subcategory])]
            else:
                self.state = State.AWAITING_CONFIRMATION
                return [f"You've selected '{self.subcategory}'. Please confirm by replying 'confirm' or restart the process by replying 'cancel'."]

        # added - recieve subsubcategory
        if self.state == State.AWAITING_SUBSUBCATEGORY:
            self.subsubcategory = message.content.lower()
            if self.subsubcategory not in self.CATEGORIES[self.category][self.subcategory]:
                return ["Invalid subsubcategory. Please specify one of the following: " + ", ".join(self.CATEGORIES[self.category][self.subcategory])]
            self.state = State.AWAITING_CONFIRMATION
            return ["You've selected " + self.subsubcategory + ". Please confirm your selection by saying 'confirm' or restart by saying 'cancel'."]

        # modified - recieve confirmation
        if self.state == State.AWAITING_CONFIRMATION:
            if message.content.lower() == 'confirm':
                self.state = State.REPORT_COMPLETE
                return ["Report confirmed. Your selection: Category - " + self.category + ", Subcategory - " + self.subcategory + 
                        (", Subsubcategory - " + self.subsubcategory if self.category == "imminent danger" and self.subcategory == "threats" else "") + ". Thank you for your report."]
            else:
                return ["Invalid response. Please confirm your selection by saying 'confirm' or restart by saying 'cancel'."]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

