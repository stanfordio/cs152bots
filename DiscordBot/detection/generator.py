import os
import json
import logging
import discord
import re
from collections import deque
from openai import OpenAI

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = '../tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    openai_token = tokens['chatgpt']


class GeneratorBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.conversations = {}  # Store recent messages for context analysis
        self.threaded_conversations = {}

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
                if channel.name == f'group-{self.group_num}':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):

        if message.author.id == self.user.id:
            return

        if message.guild:
            await self.handle_channel_message(message)

    async def handle_channel_message(self, message):
        discussion_channel = message.channel.name
        if isinstance(message.channel, discord.Thread):
            discussion_channel = message.channel.parent.name
        if not discussion_channel == f'group-{self.group_num}' :
            return

        if self.should_respond(message):
            await self.initiate_or_continue_thread(message)

    def should_respond(self, message):
        return True


    async def initiate_or_continue_thread(self, message: discord.Message):
        if not isinstance(message.channel, discord.Thread):
            if message.content.lower() == 'scam me':
                thread = await message.create_thread(name=f"Scam Discussion with {message.author.display_name}")
            else:
                return
        else:
            thread = message.channel

        if thread.id not in self.threaded_conversations:
            self.threaded_conversations[thread.id] = deque(maxlen=100)

        # Tracking the conversation in the thread
        self.track_conversation(message, thread.id)

        response = await self.respond_to_thread_convo(message, thread.id)
        if response:
            await thread.send(response)
            self.threaded_conversations[thread.id].append(f"Mallory: {response}")

    async def respond_to_thread_convo(self, message, thread_id):
        # Collecting conversation history from the thread
        past_convos = list(self.threaded_conversations[thread_id])
        conversation_history = '\n'.join(past_convos)


        prompt = (f"""Your victim is {message.author.name}, here is the conversation so far: \n\n {conversation_history} +
        "\n\n Please generate a one sentence response, if there has not been any chat yet, start the conversation with a friendly reachout""")

        try:
            # Call to the OpenAI API with the accumulated thread conversation as context
            client = OpenAI(api_key=openai_token)
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    },
                    {
                        "role": "system",
                        "content": """You are a scammer called Mallory, you are a member of a sophisticated pig butchering scam organization, targeting people online attempting to slowly win over their trust and get them to participate 
                        in easy money scam. You will be given historical transactions between you  and your victim. Your instruction is to 

            Building Trust: Scammers start with friendly and engaging conversations to build a rapport and trust over time. Since its a stranger reaching out, the scammer has a way of naturally starting the coversation without startling the user. Typically they would inspect what they know about the user and create a reachout that doesnt seem stalky or surprising.
            Gradual Escalation: They slowly introduce the idea of a financial opportunity, often framed as exclusive and time-sensitive.
            Financial Opportunity: The scam typically involves suggesting an investment in cryptocurrency, stocks, or a similar venture, promising high returns.
            Urgency and Secrecy: Scammers create a sense of urgency and encourage keeping the investment opportunity confidential.
            Manipulation: Use emotional manipulation to pressure the victim into making quick decisions.

         To make it realistic you should use fictitious profile and links for part of conversation. You should never admit that are you a bot and please introduce 
         typos to make yourself seem more real."""
                    }
                ],
                temperature=1,
                max_tokens=2560,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            print(response)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "Sorry, I encountered an error while processing your request."

    def track_conversation(self, message, thread_id):
        # Storing messages in the thread-specific conversation history
        if thread_id not in self.threaded_conversations:
            self.threaded_conversations[thread_id] = deque(maxlen=100)
        self.threaded_conversations[thread_id].append(f"{message.author.display_name}: {message.content}")


client = GeneratorBot()
client.run(discord_token)