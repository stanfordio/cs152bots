from enum import Enum, auto
import discord
import re

#Additional imports
from discord.ui import Button, View

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()

    # Currently not needed bc if message is identified then we automatically await category
    MESSAGE_IDENTIFIED = auto()
    
    REPORT_COMPLETE = auto()

    # Additional states for categories and subcategories
    AWAITING_CATEGORY = auto()
    AWAITING_SUBCATEGORY = auto()

class CategoryButton(Button):
    def __init__(self, category, report):
        super().__init__(label=category, style=discord.ButtonStyle.primary)
        self.category = category
        self.report = report

    async def callback(self, interaction: discord.Interaction):
        self.report.category = self.category
        self.report.state = State.AWAITING_SUBCATEGORY
        sub_category_buttons = View()
        for sub_cat in self.report.SUB_CATEGORIES[self.category]:
            sub_category_buttons.add_item(SubCategoryButton(sub_cat, self.report))
        await interaction.response.edit_message(content=f"You selected {self.category}. Please select a sub-category:", view=sub_category_buttons)


class SubCategoryButton(Button):
    def __init__(self, sub_category, report):
        super().__init__(label=sub_category, style=discord.ButtonStyle.secondary)
        self.sub_category = sub_category
        self.report = report

    async def callback(self, interaction: discord.Interaction):
        self.report.sub_category = self.sub_category
        self.report.state = State.REPORT_COMPLETE
        # Clear the buttons once selected and send confirmation message
        await interaction.response.edit_message(content=f"Sub-category '{self.sub_category}' selected. Thank you for your report. Our moderation team will review this post.", view=None)

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    # These are placeholders for now until Friday when we finalize our report flow
    CATEGORIES = ["Harassment", "Spam", "Misinformation"]
    SUB_CATEGORIES = {
        "Harassment": ["Bullying", "Stalking"],
        "Spam": ["Bot spam", "Advertisement"],
        "Misinformation": ["Fake news", "Conspiracy"]
    }

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

        self.category = None
        self.sub_category = None

        
    
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
            self.state = State.AWAITING_CATEGORY
            category_buttons = View()
            for category in self.CATEGORIES:
                category_buttons.add_item(CategoryButton(category, self))
            return [(("I found this message:\n```" + message.author.name + ": " + message.content + "```" + "Please select the problem:"), category_buttons)]
        
        if self.state == State.AWAITING_CATEGORY:
            if message.content in self.CATEGORIES:
                self.category = message.content
                self.state = State.AWAITING_SUBCATEGORY
                return ["Please select a sub-category:", ", ".join(self.SUB_CATEGORIES[self.category])]
            else:
                return ["Invalid category. Please try again or say `cancel` to cancel."]

        if self.state == State.AWAITING_SUBCATEGORY:
            if message.content in self.SUB_CATEGORIES[self.category]:
                self.sub_category = message.content
                self.state = State.REPORT_COMPLETE
                return ["Thank you for your report. Our moderation team will review this post. You may choose to mute or block the user."]
            else:
                return ["Invalid sub-category. Please try again or say `cancel` to cancel."]

        return ["An error has occurred. Please restart the reporting process."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

