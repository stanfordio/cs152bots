import discord
from myModal import MyModal
import uuid

tickets = {}

class ReportSelection(discord.ui.View): 
    def __init__(self, tid):
        super().__init__()
        self.tid = tid
    @discord.ui.select(placeholder='Please select reason for reporting this content', options=[
            discord.SelectOption(label='Harassment', description='description1'),
            discord.SelectOption(label='Spam', description='description2'),
            discord.SelectOption(label='Offensive Content', description='description3'),
            discord.SelectOption(label='Imminent Danger', description='description4'),
            discord.SelectOption(label='Other', description='description5')
        ])
    async def selection_callback(self, interaction:discord.Interaction, selection:discord.ui.Select):
        await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)
        tickets[self.tid] = {'reason': selection.values[0]}
        if selection.values[0] == 'Harassment':
            await interaction.followup.send(view=HarassmentSelection(self.tid),  ephemeral=True)

class HarassmentSelection(discord.ui.View):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

    @discord.ui.select(placeholder='Select Type', options=[
            discord.SelectOption(label='Sextortion', description='description1'),
            discord.SelectOption(label='Hate Speech', description='description2'),
            discord.SelectOption(label='Encouraging Self-harm', description='description3'),
            discord.SelectOption(label='Threats', description='description4'),
            discord.SelectOption(label='Other', description='description5')
        ])
    async def selection_callback(self, interaction:discord.Interaction, selection:discord.ui.Select):
        tickets[self.tid]['harassment_type'] = selection.values[0]

        await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)
        if selection.values[0] == 'Sextortion':
            await interaction.followup.send(view=SextortionTypeSelection(self.tid),  ephemeral=True)

class SextortionTypeSelection(discord.ui.View):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

    @discord.ui.select(placeholder='Select Type of Content', options=[
            discord.SelectOption(label='Content includes explicit images', description='description1'),
            discord.SelectOption(label='Content is a threat to spread explicit images', description='description2'),
        ])
    async def sextortype_callback(self, interaction:discord.Interaction, selection:discord.ui.Select):
        tickets[self.tid]['sextortion_content'] = selection.values[0]
        await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)
        await interaction.followup.send('Are these images of you or someone else?', view=ImageOwnerSelection(self.tid),  ephemeral=True)

class ImageOwnerSelection(discord.ui.View):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

    @discord.ui.button(label='Me', style=discord.ButtonStyle.red)
    async def MeOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['image_owner'] = 'Me'
        await interaction.response.send_message("Do you know the user responsible?", view=UserResponsibleSelection(self.tid), ephemeral=True)
    @discord.ui.button(label="Other", style=discord.ButtonStyle.red)
    async def OtherOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['image_owner'] = 'Other'
        await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)

class UserResponsibleSelection(discord.ui.View):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

    async def owner_choice_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
        tickets[self.tid]['image_owner'] = button.custom_id

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red, custom_id='Me')
    async def MeOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['know_responsible'] = 'Yes'
        await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)
    @discord.ui.button(label="No", style=discord.ButtonStyle.red, custom_id='Other')
    async def OtherOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['know_responsible'] = 'No'
        await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)
class MainMenuEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.title = "Main Menu Report"
        self.description = "This is the information for the Main Menu"
        self.add_field(name="Report", value="Click this to report", inline=False)
        self.add_field(name="Help", value="Click this to receive more information", inline=False)
        self.add_field(name="Talk to Moderator", value="Click this to request a private conversation with a moderator", inline=False)


class MainMenuButtons(discord.ui.View):
    def __init__(self, mod_channel):
        super().__init__()
        self.value = None
        self.mod_channel = mod_channel
        self.add_item(discord.ui.Button(label='Help', style=discord.ButtonStyle.link, url='https://www.stopsextortion.com/get-help/'))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red)
    async def reportBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        # await interaction.response.send_modal(MyModal())
        tid = uuid.uuid4()
        await interaction.response.send_message(view=ReportSelection(tid))
    
    # @discord.ui.button(label="Help", style=discord.ButtonStyle.red)
    # async def helpBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
    #     await self.mod_channel.send(f'Forwarded message:\n{interaction.user.display_name}: Help!')
    #     await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)

    @discord.ui.button(label="Talk to Mod", style=discord.ButtonStyle.red)
    async def talkBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await self.mod_channel.send(f'Forwarded message:\n{interaction.user.display_name}: Help!')
        await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)

	# async def reportBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
    #     await interaction.response.send_modal(MyModal())
    
