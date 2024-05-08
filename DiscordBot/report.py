from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_CATEGORY = auto()
    TERROR_IDENTIFIED = auto()
    MODERATE_READY = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    
    

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reported_content = None

        self.report_type = "miscellaneous"
        self.level_one_categories = ["offensive content", "harassment", "spam", "terrorist activity"]
        self.level_two_categories = ["glorification or promotion", "financing", "recruitment", "threat or incitement", "account belongs to terrorist entity"]
    
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
                self.reported_content = [guild, channel, message]
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED

            reply = "I found this message:" + "```" + message.author.name + ": " + message.content + "```"
            reply += "Please select one of the following categories for your report: \n"
            reply += "|"
            for category in self.level_one_categories:
                reply += " "
                reply += category
                reply += " |"
            return [reply]

        if self.state == State.MESSAGE_IDENTIFIED:
            try:
                if (message.content.lower() not in self.level_one_categories):
                    reply = "The category you wrote, '" + message.content + "', is not a valid category. Please reenter one of the given options. \n"
                    reply += "|"
                    for category in self.level_one_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                
                elif (message.content.lower() in self.level_one_categories and message.content.lower() != "terrorist activity"): ## category isn't terorrism but is valid
                    self.report_type = message.content
                    self.state = State.MODERATE_READY
                    reply = "Thank you for reporting a message as being " + message.content.lower() + ". We will respond appropriately!"
                    return [reply]
                
                else: ## category is terrorism
                    self.state = State.TERROR_IDENTIFIED
                    reply = "Please specify what kind of terrorist activity: \n"
                    reply += "|"
                    for category in self.level_two_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                    
            except Exception as e:
                return ["What is happening? This is: ", str(e)]

        if self.state == State.TERROR_IDENTIFIED:
            try: 
                if (message.content.lower() not in self.level_two_categories):
                    reply = "The category you wrote, '" + message.content + "', is not a valid category. Please reenter one of the given options. \n"
                    reply += "|"
                    for category in self.level_two_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                else:
                    self.report_type = message.content
                    self.state = State.MODERATE_READY
                    reply = "Thank you for reporting a message as being " + message.content.lower() + ". We will respond appropriately!"
                    return [reply]

            except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]
        
        return []
    
    def get_report_info(self):
        return [self.report_type, self.reported_content]
    
    def get_moderation_message_to_user(self):
        report_type, reported_content = self.get_report_info()
        #reported_guild = reported_content[0]
        #reported_channel = reported_content[1]
        reported_message = reported_content[2]
        if (report_type in self.level_one_categories and report_type != "terrorist activity"):
            reply = "MESSAGE_TO_REPORTED_USER \n"
            reply += reported_message.author.name + ", you have been reported for the following message: \n"
            reply += "```" + reported_message.author.name + ": " + reported_message.content + "```"
            reply += "This message was reported as " + report_type + ", which is a violation of our community guidelines \n"
            reply += "Your message has been deleted and your account has been indefinitely suspended \n"
            reply += "You may appeal by writing to fake_email@fake_platform.com"
            return [reply]
        else: ## report_type is a segment of terrorist activity
            ## will expand this to match to flow later
            reply = "MESSAGE_TO_REPORTED_USER \n"
            reply += reported_message.author.name + ", you have been reported for the following message: \n"
            reply += "```" + reported_message.author.name + ": " + reported_message.content + "```"
            reply += "This message was reported as " + report_type + ", which is a violation of our community guidelines \n"
            reply += "Your message has been deleted and your account has been indefinitely suspended \n"
            reply += "You may appeal by writing to fake_email@fake_platform.com"
            return [reply]

    def get_platform_action(self):
        report_type, reported_content = self.get_report_info()
        #reported_guild = reported_content[0]
        #reported_channel = reported_content[1]
        reported_message = reported_content[2]
        reply = "SERVER_ACTION \n"
        reply += "The following message has been deleted from the platform after a report: \n"
        reply += "```" + reported_message.author.name + ": " + reported_message.content + "```"
        return [reply]

    def report_moderate_ready(self):
        return self.state == State.MODERATE_READY

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    def end_report(self):
        self.state = State.REPORT_COMPLETE
