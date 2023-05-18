#https://www.youtube.com/watch?v=Ip0M_yxUwfg

import discord
from myModal import MyModal

class ReportButton(discord.ui.View):
	def __init__(self):
		super().__init__()

	@discord.ui.button(label="Report", style=discord.ButtonStyle.red)
	async def reportBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
		await interaction.response.send_modal(MyModal())