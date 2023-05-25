# bot.py
import asyncio
import json
import logging
import os
import re
from typing import Union

import discord
import emoji
from report import Report
from moderate import Moderate
from unidecode import unidecode

# Set up logging to the console
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")

with open(token_path) as f:
    tokens = json.load(f)
    discord_token = tokens["discord"]


class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.moderating = None # Either None or the Moderate() instance that is currently running
        self.open_reports = [] # List of all open reports

    async def on_ready(self):
        print(f"{self.user.name} has connected to Discord! It is these guilds:")
        for guild in self.guilds:
            print(f" - {guild.name}")
        print("Press Ctrl-C to quit.")

        # Parse the group number out of the bot's name
        match = re.search("[gG]roup (\d+) [bB]ot", self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception(
                "Group number not found in bot's name. Name format should be \"Group #"
                ' Bot".'
            )

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f"group-{self.group_num}-mod":
                    self.mod_channels[guild.id] = channel

    async def send_to_mod_channels(self, message: str) -> None:
        """
        Send a message to all the mod channels that this bot is configured to report to.
        """
        await asyncio.gather(
            *[channel.send(message) for channel in self.mod_channels.values()]
        )

    async def on_message(self, message):
        """
        This function is called whenever a message is sent in a channel that the bot can
        see (including DMs). Currently the bot is configured to only handle messages
        that are sent over DMs or in your group's "group-#" channel.
        """
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        """
        This function is called when a message is edited. It's called regardless of if
        the message is in the client's message cache or not.
        """
        # Ignore messages that aren't sent in a server
        if payload.guild_id is None:
            return

        # Ignore messages that are cached, on_message_edit will handle those
        if payload.cached_message:
            return

        # Get the message that was edited
        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        await self.handle_channel_message_edit(None, message)

    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        """
        This is called when a message is edited and found in this client's message cache.
        """
        # Ignore messages that aren't sent in a server
        if before.guild is None:
            return

        await self.handle_channel_message_edit(before, after)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply = f"Use the `{Report.START_KEYWORD}` command to begin the reporting process.\n"
            reply += f"Use the `{Report.CANCEL_KEYWORD}` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(
            Report.START_KEYWORD
        ):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)

        # If the report class returned a string, convert it to a list to make it easier
        if isinstance(responses, str):
            responses = [responses]

        for r in responses:
            sent_message = await message.channel.send(r)
            # if the report class returned a message with reactions, add those reactions to the message
            emojis = emoji.emoji_list(r)
            for e in emojis:
                await sent_message.add_reaction(e["emoji"])

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Handle messages sent in the "group-#" channel
        if message.channel.name == f"group-{self.group_num}":

            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(
                f"Forwarded message:\n{message.author.name}:"
                f" {self.clean_text(message.content)}"
            )
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))
        
        # Handle messages sent in the "group-#-mod" channel
        # Very similar to the handle_dm() function for handling reports
        elif message.channel.name == f"group-{self.group_num}-mod":

            # Handle a help message
            if message.content == Moderate.HELP_KEYWORD:
                reply = f"Use the `{Moderate.LIST_KEYWORD}` command to list all outstanding reports.\n"
                reply += f"Use the `{Moderate.CANCEL_KEYWORD}` command to cancel the moderation session.\n"
                await message.channel.send(reply)
                return
            
            # List all outstanding reports
            if message.content == Moderate.LIST_KEYWORD:
                for r in self.list_all_reports():
                    sent_message = await message.channel.send(r)
                return

            author_id = message.author.id
            responses = []
            

            if self.moderating == None and message.content.startswith(Moderate.START_KEYWORD):
                self.moderating = Moderate(self)
                reply = f"I'm moderating right now.\n"
                await message.channel.send(reply)
            

            # Let the moderate class handle this message; forward all the messages it returns to uss
            responses = await self.moderating.handle_message(message)


            # If the report class returned a string, convert it to a list to make it easier
            if isinstance(responses, str):
                responses = [responses]

            for r in responses:
                sent_message = await message.channel.send(r)
                # if the moderate class returned a message with reactions, add those reactions to the message
                emojis = emoji.emoji_list(r)
                for e in emojis:
                    await sent_message.add_reaction(e["emoji"])

            # If the report/moderation is complete or cancelled, remove it from our map
            if self.moderating.moderation_complete():
                self.moderating = None

            """
            # @nandini
            # Line 175 starts our section: reading messages in group-8-mod. The other parts read messages in group-8
            # which is the actual chat. So line 175 and onwards is how we respond when people send things in the
            # moderator chat. (There are only moderators in the moderator chat.)
            # I added the "list" command that lists all open reports along with their IDs. That's under the comment
            # "#List all outstanding reports" and you don't need to adjust any of that part. It's like four lines.
            
            # Here's what we were thinking of adding next, in summary:
            # If the user types something like "handle cli1grln20001rvwuslj4wo74", it starts a moderation session for that
            # specific report with the ID cli1grln20001rvwuslj4wo74. (If that ID exists.) You make a new moderation session
            # by doing self.moderating = Moderate(self). That's part of the commented-out code below.
            # self.moderating starts as None and once you type "handle something-something" it should set it to a new
            # Moderate() instance. That's the type of that.

            # The code currently commented out is the stuff that I copied from handle_dm but that is still not fully
            # adapted to work for moderator view. Here's what it would be great for you to do!
            # Number 1: Set up the moderate.py file with self.moderating.handle_message() and self.moderating.moderation_complete()
            # Number 2: Also make the moderate.py file work with the flow from https://app.diagrams.net/#G1zM8zjd6p2kEtkVCQVHSDsE0qCBl3Rq0m
            #           moderate.py should be a lot simpler than report.py because it's a much smaller flow and we also don't use
            #           reactions at any point, just 'yes' and 'no'.
            # Number 3: I can do this also, but maybe a little 'view cli1grln20001rvwuslj4wo74' command that pulls up the whole
            #           report? But maybe 'handle cli1grln20001rvwuslj4wo74' should also start by pulling up the whole report. I'm
            #           thinking if we decompose it, then 'handle' can just call 'view' and then start asking questions of the mods.

            # Okay cool! And we can turn this in a little late bc it's a made-up deadline for our own group to make the video.
            # I'll also come help work in the morning.

            # Handle starting a new moderation session (if you type something like "handle cli1grln20001rvwuslj4wo74")
            if self.moderating == None and message.content.startswith(Moderate.START_KEYWORD):
                self.moderating = Moderate(self)

            # Let the moderate class handle this message; forward all the messages it returns to us
            

            # If the moderate class returned a string, convert it to a list to make it easier
            if isinstance(responses, str):
                responses = [responses]

            for r in responses:
                sent_message = await message.channel.send(r)
            
            # If the moderate session is complete or cancelled, remove it
            if self.moderating.moderation_complete():
                self.moderating = None
            """

            


    async def handle_channel_message_edit(
        self, before: Union[discord.Message, None], after: discord.Message
    ):
        # Only handle messages sent in the "group-#" channel
        if not after.channel.name == f"group-{self.group_num}":
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[after.guild.id]
        await mod_channel.send(
            self.clean_text(
                f"Forwarded edited message by {after.author.name}:\nBefore:"
                f" {self.clean_text(before.content) if before else 'message not cached'}\nAfter:"
                f" {self.clean_text(after.content)}"
            )
        )
        scores = self.eval_text(after.content)
        await mod_channel.send(self.code_format(scores))

    def list_all_reports(self) -> [str]:
        """
        Returns a list of all reports, but formatted as strings.
        Includes a header.
        """
        if len(self.open_reports) == 0:
            return ["No open reports right now!"]
        response = [f"`{'Report ID':30} {'Priority':10} {'Reported by':20} {'Reported against':25}`"]
        self.open_reports.sort(key=lambda x: x.raw_priority, reverse=True)
        for r in self.open_reports:
            response.append(f"`{str(r.id):30} {str(r.raw_priority):10} {str(r.reporter.name):20} {str(r.message.author.name):25}`")
        return response

    def clean_text(self, text: str) -> str:
        """
        Removes special formatting from a text string so that it can be sent in a
        human-readable format to the mod channel.
        """
        # TODO: maybe also include the raw message in the mod channel?
        return unidecode(text)

    def eval_text(self, message):
        """'
        TODO: Once you know how you want to evaluate messages in your channel,
        insert your code here! This will primarily be used in Milestone 3.
        """
        return message

    def code_format(self, text):
        """'
        TODO: Once you know how you want to show that a message has been
        evaluated, insert your code here for formatting the string to be
        shown in the mod channel.
        """
        # this is where we probable will format the reporting flow
        return "Evaluated: '" + text + "'"

    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        """
        This function is called when a reaction is added to a message. It's called
        regardless of if the message is in the client's message cache or not.
        """
        reactor_id = payload.user_id

        # Ignore reactions that may have been added by the bot
        if reactor_id == self.user.id:
            return

        # Ignore reactions that aren't sent in a DM or group-8-mod channel
        channel = await self.fetch_channel(payload.channel_id)
        if channel.name != f"group-{self.group_num}-mod":
            if payload.guild_id is not None:
                return

        # We only care about adding reactions
        if payload.event_type != "REACTION_ADD":
            return
        print(self.moderating)
        # Ignore reactions that aren't part of a reporting flow or part of the moderating flow
        if reactor_id not in self.reports and self.moderating == None:
            return
        # Get the message that the reaction was added in
      
        fetched_message = await channel.fetch_message(payload.message_id)

        # Let the report class handle this reaction
        if channel.name == f"group-{self.group_num}-mod":
            responses = await self.moderating.handle_reaction_add(payload.emoji, fetched_message)
        else:
            responses = await self.reports[reactor_id].handle_reaction_add(
                payload.emoji, fetched_message
            )

        # If the report class returned a string, convert it to a list to make it easier
        if isinstance(responses, str):
            responses = [responses]

        for r in responses:
            sent_message = await channel.send(r)
            # if the report class returned a message with reactions, add those reactions to the message
            emojis = emoji.emoji_list(r)
            for e in emojis:
                await sent_message.add_reaction(e["emoji"])

        # If the report is complete or cancelled, remove it from our map
        if self.reports[reactor_id].report_complete():
            self.reports.pop(reactor_id)
        
        # If moderation is complete
        if self.moderate.moderation_complete():
            self.moderating = None


client = ModBot()
client.run(discord_token)
