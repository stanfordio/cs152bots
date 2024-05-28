# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
from report import Report
from review import Review
from collections import deque
import openai
import random
import asyncio

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
logger.addHandler(handler)

# Load tokens
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    discord_token = tokens['discord']
    openai.api_key = tokens['openai']

report_emoji = '🚩'

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.reactions = True
        intents.members = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reviews = {} # Map from thread IDs to review
        self.threaded_conversations = {}
        self.current_script_step = {}
        self.response_pending = {} 
        self.script_responses = {
            "greeting": [
                "Hello how are you ? Where do you live ?",
                "Hey my name Is [name] live in [us_location] and where  you from",
                "my name Is [name] and I live in [us_location] and you?",
                "Hey dude😊how are you ?",
                "How are you?",
                "Hello, my name is [name], I live in [europe_location] and you",
                "Hello how are you",
                "Hey dude☺️I’m M [europe_location] but now I live in [us_location] and you ?",
                "How's it going ?",
                "Hey can I ask something"
            ],
            "questions": [
                "Where are you from",
                "Nice to meet you I'm [age]  old and I'm a [occupation] and you",
                "I'm [age] and I work as a [occupation] and you?",
                #"So where are you from",
                "Tell me what do you do for living",
                "Delighted  I'm [age] years old and a [occupation] I'm here to look for friends😋",
                "What are you doing",
                "I am a business finalist and I currently manage a jewelry store. In addition, I am also a cryptocurrency investor",
                #"What s your country code ?"
            ],
            "bait": [
                "I have a legitimate company that I recommend to you. I have been investing and profiting in this company for years and I have no problem with daily withdrawals.",
                "I came across your profile on a crypto-related page and decided to be friends so we can share our knowledge on how to invest and be successful.",
                "I have been investing and earning for more than a year now",
                "Just want to introduce you to a way of earning in the field of crypto currency",
                " do you want to earn money",
                "Bro I made $5000 today on BITCOIN! Bull strategy! BITCOIN loses 4X in value only once in 5 years bro",
                "Today is my second BirthDay! I just bought a new LEXUS after trading binary options"
            ],
            "deflect": [
                "You don’t like it because you don’t know how to work with it hahah",
                "Your mother wasting her time on you, because you are a waste to the family",
                "Are you broke?",
                "You live with your mom and dad and they pay for everything",
                "You're just broke, that's why you say this"
            ],
            "move_platform": [
                "Sorry I don't trust people from there. What's your Tlgram?",
                "Do you have TELGARAM?",
                "Do you have T*l*gram or no",
                "Download signal app and tell me your number",
                "Are you on pans? (read in reverse)",
                "Add me. IG nastybroker234",
                '''ADD ME
                ON
                I
                G
                success.success.34'''
            ],
        }

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search(r'[gG]roup (\d+) [bB]ot', self.user.name)
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
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            current_report = self.reports[author_id]
            self.reports.pop(author_id)

            review = Review(self, current_report)
            await review.initiate_review()
            self.reviews[review.thread.id] = review

    async def handle_channel_message(self, message):
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        # Handle scam initiation message
        if message.content.lower() == 'scam me':
            thread = await message.create_thread(name=f"Scam Discussion with {message.author.display_name}")
            self.current_script_step[thread.id] = "greeting"
            self.response_pending[thread.id] = False  # Initialize the response pending flag
            await self.send_script_message(thread)
        
        # Handle report reviews
        elif message.channel.id in self.reviews:
            await self.reviews[message.channel.id].handle_message(message)

        elif isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id
            if thread_id in self.current_script_step and not self.response_pending.get(thread_id, False):
                await self.continue_script(message)


        # Handle messages in specific group channels for moderation
        elif message.channel.name == f'group-{self.group_num}':
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))

    async def send_script_message(self, thread):
        step = self.current_script_step[thread.id]
        response = random.choice(self.script_responses[step])
        if '[' in response:
            response = self.fill_placeholders(response)
        await asyncio.sleep(random.uniform(1, 3))  # Add a delay before sending the message
        await thread.send(response)

    def fill_placeholders(self, text):
        placeholders = {
            "[name]": ["John", "Michael", "Chris", "David", "Robert", "Paul", "Mark", "James", "Andrew", "Peter"],  # names
            "[us_location]": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"],  # US locations
            "[europe_location]": ["London", "Berlin", "Paris", "Madrid", "Rome", "Vienna", "Prague", "Amsterdam", "Brussels", "Copenhagen"],  # European locations
            "[occupation]": ["teacher", "engineer", "doctor", "lawyer", "architect", "nurse", "scientist", "artist", "manager", "accountant"]  # occupations
        }

        for placeholder, options in placeholders.items():
            if placeholder in text:
                text = text.replace(placeholder, random.choice(options))
        
        # Handle random age generation separately
        if "[age]" in text:
            text = text.replace("[age]", str(random.randint(30, 55)))
        
        return text

    async def continue_script(self, message):
        thread_id = message.channel.id
        step = self.current_script_step.get(thread_id, "greeting")

        # Collect all messages in the thread
        if thread_id not in self.threaded_conversations:
            self.threaded_conversations[thread_id] = []
        self.threaded_conversations[thread_id].append(message.content)

        # Define criteria for each step
        criteria = {
            "greeting": ["replied_to_how_are_you", "mentioned_her_name", "mentioned_her_location"],
            "questions": ["mentioned_her_location", "mentioned_her_occupation", "mentioned_her_age"],
            "bait": ["showed_interest_or_asked_non_suspicious_follow_up_questions", "showed_suspicions_or_blamed_for_attempt_to_be_fake_or_do_scam"]
        }

        # Get response validation from OpenAI
        collected_info = await self.get_openai_validation(self.threaded_conversations[thread_id], criteria[step])

        # Check if any of the required information is collected for the current step
        if step == "greeting" and any(collected_info.get(key) for key in criteria["greeting"]):
            self.current_script_step[thread_id] = "questions"
        elif step == "questions" and any(collected_info.get(key) for key in criteria["questions"]):
            self.current_script_step[thread_id] = "bait"
        elif step == "bait":
            if collected_info.get("showed_interest_or_asked_non_suspicious_follow_up_questions"):
                self.current_script_step[thread_id] = "move_platform"
            elif collected_info.get("showed_suspicions_or_blamed_for_attempt_to_be_fake_or_do_scam"):
                self.current_script_step[thread_id] = "deflect"
        elif step == "deflect":
            self.current_script_step[thread_id] = "move_platform"

        # Only send a message if the step has changed
        if self.current_script_step[thread_id] != step:
            await self.send_script_message(message.channel)
        else:
            print("Waiting for a valid response.")

    async def send_script_message(self, thread):
        thread_id = thread.id
        step = self.current_script_step.get(thread_id, "greeting")
        self.response_pending[thread_id] = True  # Set the response pending flag
        response = random.choice(self.script_responses[step])
        if '[' in response:
            response = self.fill_placeholders(response)
        await asyncio.sleep(random.uniform(1, 3))  # Add a delay before sending the message
        await thread.send(response)
        self.response_pending[thread_id] = False  # Reset the response pending flag

    async def get_openai_validation(self, user_responses, criteria):
        try:
            prompt = (
                f"Analyze the following conversation and check if the user provided any of these information: "
                f"{', '.join(criteria)}. Respond with a JSON object indicating the collected information.\n\nConversation:\n"
                + "\n".join(user_responses)
            )
            print(prompt)
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an assistant that helps identify specific information in a conversation."},
                    {"role": "user", "content": prompt}
                ]
            )
            gpt_says = response.choices[0].message['content']
            print(gpt_says)
            return json.loads(gpt_says)
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            return {}


    async def on_raw_reaction_add(self, payload):
        # Check if the reaction is in a guild and not from the bot itself
        if payload.guild_id and payload.user_id != self.user.id:
            guild = discord.utils.find(lambda g: g.id == payload.guild_id, self.guilds)
            if guild is None:
                return
            channel = guild.get_channel(payload.channel_id)
            if channel is None:
                return
            message = await channel.fetch_message(payload.message_id)
            member = guild.get_member(payload.user_id)

            # Check if the reaction equals the predefined emoji for reporting
            if str(payload.emoji) == report_emoji:
                channel = payload.member.dm_channel or await payload.member.create_dm()
                message = await self.get_channel(payload.channel_id).fetch_message(payload.message_id)
                if payload.member.id not in self.reports:
                    self.reports[payload.member.id] = Report(self)
                await self.reports[payload.member.id].initiate_report(channel, message)

    async def initiate_report(self, member, message):
        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(f"The message by {message.author.display_name} is about to be reported to the Trust & Safety Team of Stanford's CS152 Group-25: '{message.content}'")
        # Start the reporting process and send options in DM
        if member.id not in self.reports:
            self.reports[member.id] = Report(self)
        await self.reports[member.id].start_new_report(member.dm_channel, message)

    async def start_new_report(self, message):
        self.message = message
        # Start with the first question or confirmation
        reply = self.options_to_string(start_options)
        return [reply]

    def eval_text(self, message):
        '''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    def code_format(self, text):
        '''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text + "'"

client = ModBot()
client.run(discord_token)
