# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
import asyncio

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'DiscordBot/tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
    
    async def delete_reported_message(self, message_obj):
        try:
            await message_obj.delete()
            print(f"Deleted message from {message_obj.author.display_name}.")
        except discord.Forbidden:
            print("Do not have permission to delete the message.")
        except discord.NotFound:
            print("Message was not found, possibly already deleted.")
        except discord.HTTPException as e:
            print(f"Failed to delete message: {e}")

    async def notify_moderation(self, reported_message, report_reason, sub_reason):
        print("Waiting for moderation in mod channel...")

        mod_channel = self.mod_channels[reported_message.guild.id]

        mod_message = f'The message ```\n{reported_message.author.name}: "{reported_message.content}"``` is awaiting moderation for', report_reason + f": {sub_reason}"+ ". \nReact with a 👍 in the next two minutes if you believe this is a correct report, and 👎 for a false report."

        await mod_channel.send(mod_message)
        
        # check for correct reaction
        def check(reaction, user):
            return str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'

        try:
            # wait for the reaction within the two minutes
            reaction, user = await client.wait_for('reaction_add', timeout=120.0, check=check)
        except asyncio.TimeoutError:
            await mod_channel.send("The reported message has not been reacted to correctly in the timeframe -- no action was taken.")
        else:
            if str(reaction.emoji) == '👍':
                await client.delete_reported_message(reported_message)
                await mod_channel.send("The reported message has been deleted.")
            else:
                await mod_channel.send("This report is marked as a false report -- no action was taken.")
        
        return 
    
    # This is a crypto-specific moderation pathway
    async def notify_moderation_crypto(self, reported_message, report_reason, sub_reason):
        print("Waiting for crypto-specific moderation in mod channel...")

        mod_channel = self.mod_channels[reported_message.guild.id]

        #mod_message = f'The message ```\n{reported_message.author.name}: "{reported_message.content}"``` is awaiting moderation for', report_reason + f": {sub_reason}"+ "."
        await mod_channel.send(f'The message ```\n{reported_message.author.name}: "{reported_message.content}"``` is awaiting moderation for '+ report_reason + f": {sub_reason}"+ ".")
        
        scam_evidence = {"1": "Mobile App or Website Redirection", 
                         "2": "Unverified User Identity", 
                         "3": "Coercive language", 
                         "4": "Request for Moneys", 
                         "5": "Wrong DM / Unassociated with User",
                         "6": "User Misrepresentation", 
                         "7": "Other"}

        sub_reason_prompt = "Is there evidence of one or more of the following in the contents of the message? React with 👍 if yes and 👎 for no.\n"
        for number, reason in scam_evidence.items():
            sub_reason_prompt += f"{number}: {reason}\n"

        await mod_channel.send(sub_reason_prompt)
        
        # check for correct reaction
        def check(reaction, user):
            return str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'

        try:
            # wait for the reaction within the two minutes
            reaction, user = await client.wait_for('reaction_add', timeout=120.0, check=check)
        except asyncio.TimeoutError:
            await mod_channel.send("The reported message has not been reacted to correctly in the timeframe -- no action was taken.")
        else:
            print(reaction)
            if str(reaction.emoji) == '👍':
                print("Checking for crypto-specific dangerous activities...")
                # Try to learn if this is a dangerous situation
                scam_evidence = {"1": "Shared a banned website", 
                            "2": "Shared an app or link that leads to a known scam", 
                            "3": "User claims to have insider crypto or other financial information", 
                            "4": "Alleges large profits", 
                            "5": 'Offers to "trade with the user"',
                            "6": "Encourages user to download unknown investing apps (specific app may be run by scammers)", 
                            "7": "Claims to know someone who has insider investing information"}

                sub_reason_prompt = "Is there evidence of one or more of the following dangerous activity? If so, react with a 👍 and 👎 otherwise. \n"
                for number, reason in scam_evidence.items():
                    sub_reason_prompt += f"{number}: {reason}\n"

                await mod_channel.send(sub_reason_prompt)

                def check(reaction, user):
                    return str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'

                try:
                    # wait for the reaction within the two minutes
                    reaction, user = await client.wait_for('reaction_add', timeout=120.0, check=check)
                except asyncio.TimeoutError:
                    reported_users = open("DiscordBot/reported_users.txt", "a")  # append mode
                    reported_users.write(f"{reported_message.author}\n")
                    reported_users.close()
                    await client.delete_reported_message(reported_message)
                    await mod_channel.send("The reported message has not been reacted to correctly in the timeframe -- the reported account has been restricted and the message deleted.")
                else:
                    if str(reaction.emoji) == '👍':
                        # Dangerous activity warrants a ban
                        await mod_channel.send("Simulated Banning of Account -- Name added to ban list")
                        ban_file = open("banned_users.txt", "a")  # append mode
                        ban_file.write(f"{reported_message.author}\n")
                        ban_file.close()
                        await client.delete_reported_message(reported_message)
                        await mod_channel.send("The reported account has been deactivated for dangerous activity and the reported message deleted.")
                    else:
                        # Check for history of reports
                        reported_users = open('DiscordBot/reported_users.txt', 'r')

                        while True:
                            line = reported_users.readline()
                            
                            if not line:
                                break

                            print(line)
                            # If a past report exists
                            if line == str(reported_message.author) or line == str(reported_message.author) + "\n":
                                ban_file = open("DiscordBot/banned_users.txt", "a")  # append mode
                                ban_file.write(f"{reported_message.author}\n")
                                ban_file.close()
                                await client.delete_reported_message(reported_message)
                                await mod_channel.send("The reported account has been deactivated due to a history of similar reports and the reported message deleted.")
                                reported_users.close()
                                return 
                        
                        reported_users.close()
                        reported_users = open("DiscordBot/reported_users.txt", "a")  # append mode
                        reported_users.write(f"{reported_message.author}\n")
                        reported_users.close()
                        await client.delete_reported_message(reported_message)
                        await mod_channel.send("The reported account has been restricted and the reported message deleted.")

            else:
                await mod_channel.send("This report is marked as a false report -- no action was taken. ")
            

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            #print("From bot:", message.content)
            return

        print(message)

        print("From", message.author.id, ":", message.content)

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)

        if responses is None: 
            return

        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return
        
        print(message.content)

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        #await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        #await mod_channel.send(self.code_format(scores))

    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)