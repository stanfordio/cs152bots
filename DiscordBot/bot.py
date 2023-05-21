# bot.py
import json
import logging
import os
import re
from typing import Union

import discord
from report import Report
from unidecode import unidecode
import emoji

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
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
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
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f"group-{self.group_num}":
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(
            f"Forwarded message:\n{message.author.name}:"
            f" {self.clean_text(message.content)}"
        )
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

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

        # Ignore reactions that aren't sent in a DM
        if payload.guild_id is not None:
            return

        # We only care about adding reactions
        if payload.event_type != "REACTION_ADD":
            return

        # Ignore reactions that aren't part of a reporting flow
        if reactor_id not in self.reports:
            return

        # Get the channel that the reaction was added in
        channel = await self.fetch_channel(payload.channel_id)

        # Let the report class handle this reaction
        responses = self.reports[reactor_id].handle_reaction_add(payload.emoji)

        # If the report class returned a string, convert it to a list to make it easier
        if isinstance(responses, str):
            responses = [responses]

        for r in responses:
            await channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[reactor_id].report_complete():
            self.reports.pop(reactor_id)


client = ModBot()
client.run(discord_token)
