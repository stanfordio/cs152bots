import asyncio
from enum import Enum, auto
import discord
import re
import pandas as pd
import json
import logging

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    REPORT_COMPLETE = auto()

    # New States added to handle report reasons
    AWAITING_REASON = auto()
    REASON_SELECTED = auto()
    AWAITING_SUB_REASON = auto()
    AWAITING_CUSTOM_REASON = auto()
    ASK_BLOCK_USER = auto()

class Report:
    '''
    Constants
    '''
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    REPORT_REASONS = {
        "1": "Spam",
        "2": "Harmful Content",
        "3": "Harassment",
        "4": "Danger",
        "5": "Fraud", 
        "6": "Other"
    }
    SUB_REASONS = {
        "Spam": {"1": "Solicitation/Phishing", "2":"Advertisement", "3": "Malware", "4": "Impersonation"},
        "Harmful Content": {"1": "Misinformation", "2": "Intellectual Property Violation", "3": "Sexually Explicit Content", "4": "Graphic Violence", "5": "Other"},
        "Harassment": {"1": "Bullying", "2": "Sexual Harassment", "3": "Racial Harassment", "4": "Gender Harassment", "5": "Personal Information", "5": "Other"},
        "Danger": {"1": "Stalking", "2": "Threats of Violence", "3": "Illegal activities", "4": "Exploitative Content", "5": "Other"},
        "Fraud" : {"1": "Crypto Scam", "2": "Online Job Scam", "3": "Fake Investment Scam", "4": "Other"}, 
        "Other": {"1": "I am uncomfortable with this content.", "2": "Other"}
    }



    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None # To store the discord.Message object
        self.reported_message = None
        self.report_reason = ""  # To store the reason for the report
    
    async def fetch_message_from_link(self, link):
        # Example: link format "https://discord.com/channels/123456789012345678/987654321098765432/567890123456789012"
        match = re.search(r'/channels/(\d+)/(\d+)/(\d+)', link)
        if match:
            guild_id, channel_id, message_id = map(int, match.groups())
            guild = self.client.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    self.message = await channel.fetch_message(message_id)
                except discord.NotFound:
                    print("Message not found during fetch.")
                except discord.Forbidden:
                    print("No permission to fetch the message.")
                except discord.HTTPException as e:
                    print(f"Failed to fetch message: {e}")

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
            reply += "Say `help` at any time for more information, and `cancel` to abort this report.\n\n"
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
            reason_prompt = "Why are you reporting this message? Type the number:\n"
            for number, reason in self.REPORT_REASONS.items():
                reason_prompt += f"{number}: {reason}\n"
            return [reason_prompt]
        
        if self.state == State.AWAITING_REASON:
            if message.content.strip() in self.REPORT_REASONS:
                self.report_reason = self.REPORT_REASONS[message.content.strip()]
                if self.report_reason == "Other":
                    self.state = State.AWAITING_CUSTOM_REASON
                    return ["Please type your specific reason for reporting:"]
                else:
                    sub_reason_prompt = "Please select the specific issue:\n"
                    for number, reason in self.SUB_REASONS[self.report_reason].items():
                        sub_reason_prompt += f"{number}: {reason}\n"
                    self.state = State.AWAITING_SUB_REASON
                    return [sub_reason_prompt]
            else:
                return ["Invalid selection. Please enter a valid number for the reason."]
        
        if self.state == State.AWAITING_SUB_REASON:
            if message.content.strip() in self.SUB_REASONS[self.report_reason]:
                self.sub_reason = self.SUB_REASONS[self.report_reason][message.content.strip()]

                # For Crypto Scams -- our specific abuse -- follow a certain mod pathway
                if self.sub_reason == "Crypto Scam":
                    await message.channel.send(f"Thank you for the report. Reason: {self.report_reason}. Specific issue: {self.sub_reason}.")
                    await message.channel.send("A member of the moderation team will evaluate it soon.")

                    print("Sending to Moderation -- Cryto-Scam Specific")
                    send_moderation = asyncio.create_task(self.client.notify_moderation_crypto(self.message, self.report_reason, self.sub_reason))
                    await send_moderation
                # For all other scams, follow a generic pathway
                else:
                    await message.channel.send(f"Thank you for the report. Reason: {self.report_reason}. Specific issue: {self.sub_reason}.")
                    await message.channel.send("A member of the moderation team will evaluate it soon.")


                    print("Sending to Moderation")
                    send_moderation = asyncio.create_task(self.client.notify_moderation(self.message, self.report_reason, self.sub_reason))
                    await send_moderation

                self.state = State.ASK_BLOCK_USER
                return ["In the meantime, would you like to block the user? Reply with 'y' for yes or 'n' for no."]
                #return [f"Thank you for the report. Reason: {self.report_reason}. Specific issue: {self.sub_reason}. Your report has been filed and the message has been deleted. Would you like to block the user? Reply with 'y' for yes or 'n' for no."]
            else:
                return ["Invalid selection. Please enter a valid number for the specific issue."]
        
        if self.state == State.AWAITING_CUSTOM_REASON:
            self.sub_reason = message.content 
            self.state = State.ASK_BLOCK_USER
            if self.message:
                await self.client.delete_reported_message(self.message)
            
            await message.channel.send(f"Thank you for the report. Reason: {self.report_reason}. Custom issue: {self.sub_reason}.")
            await message.channel.send("A member of the moderation team will evaluate it soon.")
            await self.client.notify_moderation(self.message, self.report_reason, self.sub_reason)

            self.state = State.ASK_BLOCK_USER
            return ["In the meantime, would you like to block the user? Reply with 'y' for yes or 'n' for no."]
                
        

        # TODO: IMPLEMENT FUNCTION TO BLOCK USER
        # This is currently temporary
        if self.state == State.ASK_BLOCK_USER:
            if message.content.lower() == 'y':
                # TODO: CREATE FUNCTION HERE
                # await self.client.block_user(self.message.author)
                self.state = State.REPORT_COMPLETE
                return ["The user has been blocked. Thank you for your report."]
            elif message.content.lower() == 'n':
                self.state = State.REPORT_COMPLETE
                return ["You have chosen not the block the user. Thank you for your report."]
            else:
                return ["Invalid response. Please reply with 'y' for yes or 'n' for no."]

        
        if self.state == State.REPORT_COMPLETE:
            return [""]

        return []


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

