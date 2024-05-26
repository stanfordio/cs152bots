from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_CATEGORY = auto()
    TERROR_IDENTIFIED = auto()
    HARASSMENT_IDENTIFIED = auto()
    SPAM_IDENTIFIED = auto()
    OFFENSIVE_CONTENT_IDENTIFIED = auto()
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
        self.harassment_categories = ["bullying", "hate speech"]
        self.spam_categories = ["solicitation", "impersonation"]
        self.offensive_categories = ["physical abuse", "nudity or sexual content", "self harm or suicide", "violent threat", "human trafficking", "graphic violence"]
        self.terrorism_categories = ["glorification or promotion", "financing", "recruitment", "direct threat or incitement", "account represents terrorist entity"]
        #self.target_identity = ["me", "someone else"]
    
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
            reply =  "Thank you for starting the reporting process!! "
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
                
                # harassment flow
                elif (message.content.lower() == "harassment"):
                    self.report_type = "harassment"
                    self.state = State.HARASSMENT_IDENTIFIED
                    reply = "Please specify the type of harassment: \n"
                    reply += "|"
                    for category in self.harassment_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]

                #spam flow
                elif (message.content.lower() == "spam"):
                    self.report_type = "spam"
                    self.state = State.SPAM_IDENTIFIED
                    reply = "Please specify the type of spam: \n"
                    reply += "|"
                    for category in self.spam_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                
                else:
                    self.state = State.TERROR_IDENTIFIED
                    reply = "Please specify the type of terrorist activity: \n"
                    reply += "|"
                    for category in self.terrorism_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]

                #offensive content flow
                    self.report_type = "offensive content"
                    self.state = State.OFFENSIVE_CONTENT_IDENTIFIED
                    reply = "Please specify the type of offensive content: \n"
                    reply += "|"
                    for category in self.offensive_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]

                """
                elif (message.content.lower() in self.level_one_categories and message.content.lower() != "terrorist activity"): ## category isn't terorrism but is valid
                    self.report_type = message.content.lower()
                    self.state = State.MODERATE_READY
                    reply = "Thank you for reporting a message as being " + message.content.lower() + ". The content moderation team will review the post and determine the appropriate action, which may include removal of the post or suspension of the account."
                    return [reply]
                """
               
                    
            except Exception as e:
                return ["What is happening? This is: ", str(e)]

        #follow up questions on report of SPAM
        if self.state == State.SPAM_IDENTIFIED:
            try: 
                if (message.content.lower() not in self.spam_categories):
                    reply = "The category you wrote, '" + message.content + "', is not a valid category. Please reenter one of the given options. \n"
                    reply += "|"
                    for category in self.spam_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                else:
                    self.report_type = message.content.lower()
                    self.state = State.MODERATE_READY
                    reply = "Thank you for reporting a post including " + message.content.lower() + " The content moderation team will review the activity and determine the appropriate action, which may include removal of the post and/or suspension of the offending account. "
                    return [reply]

            except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]

        # follow up on HARASSMENT report
        if self.state == State.HARASSMENT_IDENTIFIED:
            try: 
                if (message.content.lower() not in self.harassment_categories):
                    reply = "The category you wrote, '" + message.content + "', is not a valid category. Please reenter one of the given options. \n"
                    reply += "|"
                    for category in self.harassment_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                else: # how to add follow up question on target of harassment??
                    self.report_type = message.content.lower()
                    self.state = State.MODERATE_READY
                    reply = "Thank you for reporting a post including " + message.content.lower() + " The content moderation team will review the activity and determine the appropriate action, which may include removal of the post and/or suspension of the offending account. Would you like to block the user?"
                    # need to add another layer of response for blocking
                    return [reply]

            except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]

        # follow up on OFFENSIVE CONTENT report
        if self.state == State.OFFENSIVE_CONTENT_IDENTIFIED:
            if (message.content.lower() not in self.offensive_categories):
                reply = "The category you wrote, '" + message.content + "', is not a valid category. Please reenter one of the given options. \n"
                reply += "|"
                for category in self.terrorism_categories:
                    reply += " "
                    reply += category
                    reply += " |"
                return [reply]
            else:
                self.report_type = message.content.lower()
                self.State = State.MODERATE_READY
                reply = "Thank you for reporting offensive content including " + message.content.lower() + ". We take the safety of our users and communities seriously. If you or someone else is in imminent danger, please call 911. The content moderation team will review the activity and determine the appropriate action, which may involve contacting local authorities, removing the post, and suspending the offending account."
        
        #follow up on TERRORISM
        if self.state == State.TERROR_IDENTIFIED:
            try: 
                if (message.content.lower() not in self.terrorism_categories):
                    reply = "The category you wrote, '" + message.content + "', is not a valid category. Please reenter one of the given options. \n"
                    reply += "|"
                    for category in self.terrorism_categories:
                        reply += " "
                        reply += category
                        reply += " |"
                    return [reply]
                else:
                    self.report_type = message.content.lower()
                    self.state = State.MODERATE_READY
                    if self.report_type == "account belongs to terrorist entity":
                        reply = "Thank you for reporting a post because the " + message.content.lower() + ". We take the safety of our users and communities seriously. The content moderation team will review the activity and determine the appropriate action, which may involve contacting local authorities. "
                    else:
                        reply = "Thank you for reporting a post incudling " + message.content.lower() + " of terrorism. We take the safety of our users and communities seriously. The content moderation team will review the activity and determine the appropriate action, which may involve contacting local authorities. "
                    return [reply]

            except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]
        
        if self.state == State.REPORT_COMPLETE:
            try:
                return ["Stop"]
            
            except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]

        return []
    
    def get_report_info(self):
        return [self.report_type, self.reported_content]
    
    def get_moderation_message_to_user(self):
        try:
            report_type, reported_content = self.get_report_info()
            #reported_guild = reported_content[0]
            #reported_channel = reported_content[1]
            reported_message = reported_content[2]
            if (report_type in self.level_one_categories and report_type != "terrorist activity"):
                reply = " \nMESSAGE_TO_REPORTED_USER (pending moderator approval) \n"
                reply += reported_message.author.name + ", you have been reported for the following post: \n"
                reply += "```" + reported_message.author.name + ": " + reported_message.content + "```"
                reply += "This post was reported as " + report_type + ", which is a violation of our community guidelines \n"
                reply += "Your post has been removed and your account has been indefinitely suspended \n"
                reply += "You may appeal by writing to fake_email@fake_platform.com" + "\n-\n-\n"
                return reply
            else: ## report_type is a segment of terrorist activity
                ## will expand this to match to flow later
                reply = " \nMESSAGE_TO_REPORTED_USER (pending moderator approval) \n"
                reply += reported_message.author.name + ", you have been reported by a user for the following message: \n"
                reply += "```" + reported_message.author.name + ": " + reported_message.content + "```"
                reply += "This post was reported as " + report_type + ", which is a violation of our community guidelines \n"
                if report_type == "account belongs to terrorist entity":
                    reply += "We do not allow accounts that support or are otherwise affiliated with terrorist entities on our platform \n"
                else:
                    reply += "We do not allow content that promotes, supports, glorifies, or incites terrorist activity\n"
                reply += "Your post has been deleted and your account has been indefinitely suspended \n"
                reply += "You may appeal by writing to fake_email@fake_platform.com" + "\n-\n-\n"
                return reply
            
        except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]

    def get_platform_action(self):
        try:
            report_type, reported_content = self.get_report_info()

            reported_message = reported_content[2]
            reply = "\nSERVER_ACTION (pending moderator approval)\n"
            reply += "The following post has been deleted from the platform after a report, and the user has been temporarily/indefinitely suspended: \n"
            reply += "```" + reported_message.author.name + ": " + reported_message.content + "```"

            if report_type == "glorification or promotion":
                reply += "The content has been also been uploaded to the GIFCT hash bank if it wasn't already."

            elif report_type in self.terrorism_categories:
                reply += "A report of this incident has been sent to local authorities and/or the FBI, including the nature of the violation, user information, and activity."

            reply += "\n-\n-\n"
            return reply
        
        except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]

    def report_moderate_ready(self):
        try:
            return self.state == State.MODERATE_READY
        
        except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]

    def report_complete(self):
        try:
            return self.state == State.REPORT_COMPLETE
        except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]
    
    def end_report(self):
        try:
            self.state = State.REPORT_COMPLETE
        except Exception as e:
                return ["Uhhhh, here's an error: ", str(e)]
