import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
from discord.components import SelectOption
from discord.ui import Select, View

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
    
class ModeratorActionDropdown(Select):
    def __init__(self, mod_channel):
        super().__init__(placeholder="What actions do you want to take?", min_values=1, max_values=1)
        self.mod_channel = mod_channel
        self.add_option(label="Ban User", description="Ban the actor from the server", value="Actor has been banned")
        self.add_option(label="Remove Post", description="Remove the post from the channel", value="Post has been removed")
        self.add_option(label="Report User to Discord", description="Report the User to Discord", value="Actor has been reported to Discord")
        self.add_option(label="Place User on Probation", description="Place the actor on temporary probation", value="Actor has been placed on temporary probation")

    async def callback(self, interaction):
        action_status = f'Action taken: {self.values[0]}. Thank you for moderating this report!'
        await self.mod_channel.send(action_status)
        await interaction.response.defer()
    
class LegitimacyDropdown(Select):
    def __init__(self, mod_channel):
        super().__init__(placeholder="Is this report legitimate?", min_values=1, max_values=1)
        self.mod_channel = mod_channel
        self.add_option(label="Yes", description="This report is legitimate", value="legitimate")
        self.add_option(label="No", description="This report is not legitimate", value="not_legitimate")

    async def callback(self, interaction):
        await interaction.response.defer()
        report_status = f'Report legitimacy marked as: {self.values[0]}'
        if self.values[0] == "legitimate":
            view = View()
            view.add_item(ReportReasonDropdown(self.mod_channel))
            await self.mod_channel.send(content=f"{report_status}\nPlease verify the reason for reporting:", view=view)
        else:
            await self.mod_channel.send(report_status)

class ReportReasonDropdown(Select):
    def __init__(self, mod_channel):
        options = [
            SelectOption(emoji="📫", label='Blackmail', value='Blackmail', description="You are being threatened to send cryptocurrency"),
            SelectOption(emoji="💰", label='Investment Scam', value='Investment Scam', description="You sent cryptocurrency to a fraudulent individual"),
            SelectOption(emoji="🔗", label='Suspicious Link', value='Suspicious Link', description="You received a link that may lead to a disreputable site"),
            SelectOption(emoji="⚠️", label="Imminent Danger", value="Imminent Danger", description="You are in immediate danger"),
            SelectOption(emoji="❓", label="Other", value="Other", description="You have a different reason for reporting")
        ]
        super().__init__(placeholder='Verify the reason for reporting', min_values=1, max_values=1, options=options)
        self.mod_channel = mod_channel

    async def callback(self, interaction):
        report_status = f'Report reason verified as: {self.values[0]}'
        await self.mod_channel.send(report_status)
        await interaction.response.defer()
        if self.values[0] in ["Imminent Danger", "Investment Scam", "Blackmail"]:
            prompt_message = "Please type a message that can be sent to the authorities regarding this case."
            await self.mod_channel.send(prompt_message)
            await interaction.client.wait_for_user_reply(self.mod_channel, interaction.user)
        
        action_view = View()
        action_view.add_item(ModeratorActionDropdown(self.mod_channel))
        await self.mod_channel.send("Select the action you want to take:", view=action_view)

def create_legitimacy_view(mod_channel):
    view = View()
    view.add_item(LegitimacyDropdown(mod_channel))
    return view

def create_report_reason_view(mod_channel):
    view = View()
    view.add_item(ReportReasonDropdown(mod_channel))
    return view

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
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

        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                    
    async def wait_for_user_reply(self, channel, user):
        def check(m):
            return m.author == user and m.channel == channel

        try:
            message = await self.wait_for('message', check=check, timeout=300)
            await channel.send(f"Thank you for your response, {user.name}. A report has been filed with the authorities. Please wait for further instructions.")
        except asyncio.TimeoutError:
            await channel.send("You did not respond in time.")

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

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r.get("response"), view=r.get("view"))
            if r.get("summary"):
                mod_channel = self.mod_channels[r.get("reported_message").guild.id]
                view = create_legitimacy_view(mod_channel)
                await mod_channel.send(r.get("summary"), view=view)


        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    
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