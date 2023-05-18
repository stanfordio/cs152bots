# Source: https://www.youtube.com/watch?v=Raed5GgR0CU

import discord
from discord.ext import commands
from colorama import Back, Fore, Style
import time
import json
import platform
from discord import ui

class MyModal(ui.Modal):
	question1 = ui.TextInput(label="This is a question with short text input", style=discord.TextStyle.short)
	question2 = ui.TextInput(label="This is a question with long text input", style=discord.TextStyle.long)
	button1 = ui.Button(label="It's a button", custom_id=button1)
	button2 = ui.Button(label="Wow", custom_id=button2)

	async def on_submit(self, interaction: discord.Interaction):
		await interaction.response.send_message("You filled out the form.")