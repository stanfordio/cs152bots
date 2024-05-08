import asyncio
from enum import Enum, auto
import discord
import re
import pandas as pd
import json

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    REPORT_COMPLETE = auto()

    # New States added to handle report reasons
    AWAITING_REASON = auto()
    RECEIVED_REASON = auto()
    AWAITING_MODERATION = auto()
    LOG_REPORT = auto()

class Report:
    '''
    Constants
    '''
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    REASON_CHOICES = ["Suspicious Link", "Harmful Content", "Harassment"]
    DEFAULT_REPORT_DICTIONARY = {
        "total_reports" : 1,
        "Suspicious Link" : 0,
        "Harmful Content" : 0,
        "Harassment" : 0
        }

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None # To store the discord.Message object
        self.reported_message = None
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
            self.reported_message = self.message
            return ["I found this message:", f"```{self.message.author.name}: {self.reported_message.content}```",
                    "What is the reason you reported this message? Please type clearly, taking mind of caps and spaces.",
                    "- Suspicious Link\n- Harmful Content\n- Harassment"]

        # Wait for reason
        if self.state == State.AWAITING_REASON:
            print("Awaiting reason...")
            # Store the reason for the report
            if message.content not in self.REASON_CHOICES:
                return [f"Invalid Report Reason. Please retry, typing or copying the options originally listed, or type CANCEL to cancel this operation."]
            else:
                self.report_reason = message.content  

            self.state = State.RECEIVED_REASON
            #return [f"You've logged \"{self.report_reason}\" as the reason for your report."]
            reply = "You've logged \"" + self.report_reason + "\" as the reason for your report."
            await message.channel.send(reply)
            #return 

        
        # The report_reason is valid in this case, we want to execute specific report pathways
        #if self.state == State.RECEIVED_REASON:
            print("Received reason...")

            if self.report_reason == "Suspicious Link":
                print("Report is Suspicious Link")
                # Investigate Suspicious Link
                # Forward to moderation team to check
                await self.send_for_moderation()
                self.state == State.LOG_REPORT
            elif self.report_reason == "Harmful Content":
                # 
                pass
            elif self.report_reason == "Harassment":
                pass
            elif self.report_reason == "":
                pass

            return


        # Creates a log report, based on what the report reason is
        if self.state == State.LOG_REPORT:
            f = open('DiscordBot/users_log.json')
            users_log = json.load(f)

            # If user exists, update
            if message.author.name in users_log:
                users_log[message.author.name] += 1
                users_log[message.author.name][self.report_reason] += 1
            # Otherwise, add in the new user
            else:
                users_log[message.author.name] = self.DEFAULT_REPORT_DICTIONARY
                users_log[message.author.name][self.report_reason] += 1


            # Write to log file
            with open('DiscordBot/users_log.json', 'w', encoding='utf-8') as f:
                json.dump(users_log, f)

            print(users_log)

            self.state == State.REPORT_COMPLETE
            return ["Thank you for the report. I've incremented", message.author.name + "'s report count to " + str(users_log[message.author.name]) + "."]
            

        return []

    async def send_for_moderation(self):
        print("Waiting for moderation in mod channel...")

        mod_channel = self.mod_channels[self.reported_message.guild.id]
        await mod_channel.send(f'The message ```\n{self.reported_message.author.name}: "{self.reported_message.content}"``` is awaiting moderation for', self.report_reason + ".")
        
        def check(reaction, user):
            return user == self.message.author and str(reaction.emoji) == '👍'

        try:
            reaction, user = await mod_channel.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await mod_channel.send('👎')
        else:
            await mod_channel.send('👍')


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

