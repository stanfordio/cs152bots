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
	@ui.button(label="It's a button")
	async def buttonMethod1(self, interaction: discord.Interaction, Button: ui.Button):
		await interaction.response.send_message("Pressed button 1")
	@ui.button(label="Wow")
	async def buttonMethod2(self, interaction: discord.Interaction, Button: ui.Button):
		await interaction.response.send_message("Pressed button 2")

	async def on_submit(self, interaction: discord.Interaction):
		await interaction.response.send_message("You filled out the form.")