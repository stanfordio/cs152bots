from enum import Enum, auto
import discord
import re

class State(Enum):
    START = auto()
    THREAT_LEVEL = auto()

class Moderate:
    def __init__(self, mod_channel, message):
        self.state = State.START
        self.mod_channel = mod_channel
        self.violations = {}

    async def start_mod_flow(self):
        await self.mod_channel.send("How much of a threat is this? (minor, moderate, major)")
        self.state = State.THREAT_LEVEL

    async def handle_message(self, message):
        if self.state == State.THREAT_LEVEL:
            if message.lower() == "minor":
                await self.mod_channel.send("then it's fine tbh, dw bout it")

    async def add_violation(self, userId):
        if userId in self.violations:
            self.violations[userId] += 1
        else:
            self.violations[userId] = 1


    async def moderate_content(self, message, userID, hateSpeech):
        reply = f"Content: {message}\nIs this content hate speech? {'Yes' if hateSpeech else 'No'}"
        # Present the moderation options
        reply += "Choose an action:"
        reply += "1: Remove comment."
        reply += "2: Remove comment and mute account for 24 hours."
        reply += "3: Remove comment, mute account for 24 hours, and ban account."
        reply += "Enter the number of the action you wish to take: "
        self.state = State.AWAITING_MESSAGE
        # action_choice = input("Enter the number of the action you wish to take: ")

        self.add_violation(userID)

        if message.content == "1":
            reply = "We will remove the comment."
        elif message.content == "2":
            reply = f"We will remove the comment and mute {userID}'s account for 24 hours."
        elif message.content == "3":
            reply = f"We will remove the comment and ban {userID}'s account."
        else:
            reply = "Invalid action."

        

        