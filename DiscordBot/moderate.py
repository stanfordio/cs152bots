from enum import Enum, auto
import discord
import re

class State(Enum):
    START = auto()
    THREAT_LEVEL = auto()

class Moderate:
    def __init__(self, mod_channel, id, report):
        self.state = State.START
        self.mod_channel = mod_channel

    async def start_mod_flow(self):
        await self.mod_channel.send("How much of a threat is this? (minor, moderate, major)")
        self.state = State.THREAT_LEVEL

    async def handle_message(self, message):
        print('hello')
        await self.mod_channel.send("Moooooo i'm working")


        # if self.state == State.THREAT_LEVEL:
        #     if message.lower() == "minor":
        #         await self.mod_channel.send("then it's fine tbh, dw bout it")
        