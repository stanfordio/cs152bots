import discord
from myModal import MyModal

class MainMenuEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.title = "Main Menu Report"
        self.description = "This is the information for the Main Menu"
        self.add_field(name="Report", value="Click this to report", inline=False)
        self.add_field(name="Help", value="Click this to receive more information", inline=False)
        self.add_field(name="Talk to Moderator", value="Click this to request a private conversation with a moderator", inline=False)


class MainMenuButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
    
    @discord.ui.button(label="Report", style=discord.ButtonStyle.red)
    async def reportBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await interaction.response.send_modal(MyModal())
    
    @discord.ui.button(label="Help", style=discord.ButtonStyle.red)
    async def helpBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await interaction.response.send_message("You clicked the help button")

    @discord.ui.button(label="Talk to Mod", style=discord.ButtonStyle.red)
    async def talkBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await interaction.response.send_message("You clicked the talk to moderator button")

	# async def reportBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
    #     await interaction.response.send_modal(MyModal())
    
