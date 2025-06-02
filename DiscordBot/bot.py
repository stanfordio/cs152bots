# bot.py
import discord
import os
import json
import logging
import re
from report import Report
from review import Review

# --- ML model setup -------------------------------------------------
import torch
from transformers import AutoTokenizer
from classifier import TextClassifier      #

BASE_MODEL    = "Alibaba-NLP/gte-multilingual-base"
WEIGHTS_PATH  = "Alibaba-NLP-gte-multilingual-base.pt"   # same folder as bot.py
LABEL_MAP     = {0: "benign", 1: "lgbtq_hate"}

TOKENIZER = AutoTokenizer.from_pretrained(BASE_MODEL, model_max_length=64)

model = TextClassifier(base_model_name=BASE_MODEL, num_classes=len(LABEL_MAP))
state_dict = torch.load(WEIGHTS_PATH, map_location="cpu")
model.load_state_dict(state_dict, strict=False)
model.eval()                               # inference mode
# --------------------------------------------------------------------

import asyncio

async def classify_text(text: str) -> str:
    """Return 'benign' or 'lgbtq_hate' for a given message."""
    def _predict(t):
        inputs = TOKENIZER(t, return_tensors="pt",
                           truncation=True, padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits
        pred_id = int(torch.argmax(logits, dim=-1).item())
        return LABEL_MAP[pred_id]

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _predict, text)

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reports_to_review = {} # Stores channel messages in mod channel to review
        self.name_to_id = {} #Map from a user name (written in message in mod channel) to user id (used to get correct report for user)
        self.manual_reviews = {} #Map from moderator id to review

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

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        self.name_to_id[message.author.name] = message.author.id
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

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
        if author_id not in self.reports and not message.content.lower().startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self, message.author)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            for guild in self.guilds:
                for channel in guild.text_channels:
                    if channel.name == f'group-{self.group_num}-mod':
                        mod_channel_message = await channel.send(
                                           f"""Message reported by: {message.author.name}\n"""
                                           f"""Reported message author: {self.reports[self.name_to_id[message.author.name]].target_message.author.name}\n"""
                                           f"""Reported message content: "{self.reports[self.name_to_id[message.author.name]].target_message.content}\n"""
                                           f"""**Report Details**\n{self.reports[self.name_to_id[message.author.name]].formatted_report_details}"""
                        )
                        self.reports_to_review[mod_channel_message.id] = self.reports[author_id]
                        await channel.send("Type 'review' to manually review the reported message" )
                        self.reports.pop(author_id)
    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if message.channel.name == f'group-{self.group_num}':
    
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            scores = await self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))
        
        elif message.channel.name == f'group-{self.group_num}-mod':
            # Handle a help message
            if message.content == Review.HELP_KEYWORD:
                reply =  "Use the `review` command to begin the review process.\n"
                reply += "Use the `cancel` command to cancel the review process.\n"
                await message.channel.send(reply)
                return

            author_id = message.author.id
            responses = []

            # Only respond to messages if they're part of a reporting flow
            if author_id not in self.manual_reviews and not message.content.lower().startswith(Review.START_KEYWORD):
                return

            # If we don't currently have an active review for this moderator, add one
            if author_id not in self.manual_reviews:
                self.manual_reviews[author_id] = Review(self)

            # Let the review class handle this message; forward all the messages it returns to us
            responses = await self.manual_reviews[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)


    
    async def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''

        return await classify_text(message)
        

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)