from enum import Enum, auto
import discord
import re
import pandas as pd
import json

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    # New State Added to handle awaiting the reason for the report
    AWAITING_REASON = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None # To store the discord.Message object
        self.report_reason = ""  # To store the reason for the report
    
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
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.AWAITING_REASON
            return ["I found this message:", f"```{self.message.author.name}: {self.message.content}```",
                    "What is the reason you reported this message?",
                    "- Spam", "- Harmful Content", "- Harassment", "- Danger", "- Other"]

        if self.state == State.AWAITING_REASON:
            self.report_reason = message.content  # Store the reason for the report
            self.state = State.REPORT_COMPLETE
            # Optionally, log the report or perform other actions here
            return [f"Thank you for the report. Reason: {self.report_reason}. Your report has been filed."]
            #return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #        "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
        

        # USED LATER
        if self.state == State.MESSAGE_IDENTIFIED:
            f = open('DiscordBot/users_log.json')
            users_log = json.load(f)

            # If user exists, update
            if message.author.name in users_log:
                users_log[message.author.name] += 1
            # Otherwise, add in the new user
            else:
                users_log[message.author.name] = 1

            # Write to log file
            with open('DiscordBot/users_log.json', 'w', encoding='utf-8') as f:
                json.dump(users_log, f)

            print(users_log)

            self.state == State.REPORT_COMPLETE
            return ["Thank you for the report. I've incremented", message.author.name + "'s report count to " + str(users_log[message.author.name]) + "."]
            

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

