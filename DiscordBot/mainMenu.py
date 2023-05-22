import discord
from myModal import MyModal
import uuid
import time
from dataclasses import dataclass

tickets = {}

def get_drop_down_options(elems : dict[str, str]) -> list[discord.SelectOption]:
        return [discord.SelectOption(label=l, description=d) for l, d in elems.items()]

# TODO: figure out what bot's type is
async def create_completionEmbed(bot, tid : int):
    embed = CompletionEmbed(bot, tid)

    if 'message_link' in tickets[tid].keys():
        # link = 'https://discord.com/channels/1103033282779676743/1103033287250804838/1109919564701126787'
        link = tickets[tid]['message_link'].split('/')
        # FIXME This indexes out of bounds.
        message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(int(link[-1]))

        tickets[tid]['message'] = message.content
        tickets[tid]['msg_user_id'] = message.author

    for key, value in tickets[tid].items():
        embed.add_field(name=key, value=value)
    
    return embed

class CompletionEmbed(discord.Embed):
    def __init__(self, bot, tid : int):
        super().__init__()
        self.tid = tid
        self.bot = bot
        self.title = 'Summary of Report Request'
        self.description = \
                '"Thank you. We will investigate further. \
                Please expect a response within the next 36 hours."'
        self.add_field(name='Ticket ID', value=tid)

"""
Prompt: "Please select reason for reporting this content"
"""
class ReportSelection(discord.ui.View): 
    def __init__(self, bot, tid):
        super().__init__()
        self.bot = bot
        self.tid = tid

    
    @discord.ui.select(placeholder='Please select reason for reporting this content', \
        options=get_drop_down_options({
                'Harassment'         : 'description1',
                'Spam'               : 'description2',
                'Offensive Content'  : 'description3',
                'Imminent Danger'    : 'description4',
                'Other'              : 'description5'
        })
    )
    async def selection_callback(self, \
        interaction : discord.Interaction, \
        selection : discord.ui.Select):
        # await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)

        tickets[self.tid] = {'reason': selection.values[0]}
        reason = ExplanationModal(selection.values[0], self.tid)
        await interaction.response.send_modal(reason)
        await reason.wait()
        time.sleep(1)

        if selection.values[0] == 'Harassment':
            await interaction.followup.send("You chose: Harassment", view=HarassmentSelection(self.bot, self.tid), ephemeral=True)
        else:
            # reason = ExplanationModal(selection.values[0], self.tid)
            # await interaction.response.send_modal(reason)
            # await reason.wait()
            # time.sleep(3)
            await interaction.followup.send(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True) 


class ExplanationModal(discord.ui.Modal):
    def __init__(self, choice, tid):
        super().__init__(title=f"Your report reasoning is: {choice}")
        self.tid = tid

        self.add_item(discord.ui.TextInput(label="Paste Message Link ", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="Please explain your reasoning", style=discord.TextStyle.long))

    async def on_submit(self, interaction: discord.Interaction):
        tickets[self.tid]['message_link'] = self.children[0].value
        tickets[self.tid]['reason'] = self.children[1].value
        await interaction.response.send_message("Thank you for your response!")
        self.stop()
"""
Prompt: Harassment: Select Type
"""
class HarassmentSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot

    @discord.ui.select(placeholder='Select Type',
         options=get_drop_down_options({
            'Sextortion'                : 'description1',
            'Hate Speech'               : 'description2',
            'Encouraging Self-harm'     : 'description3',
            'Threats'                   : 'description4',
            'Other'                     : 'description5'
        })
    )
    async def selection_callback(self, interaction:discord.Interaction, selection:discord.ui.Select):
        tickets[self.tid]['harassment_type'] = selection.values[0]

        await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)

        if selection.values[0] == 'Sextortion':
            await interaction.followup.send(view=SextortionTypeSelection(self.bot, self.tid),  ephemeral=True)
        else:
            await interaction.followup.send(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True)

"""
Prompt: Sextortion - Select Type of Content
"""
class SextortionTypeSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot

    @discord.ui.select(placeholder='Select Type of Content', options=get_drop_down_options({
            'Content includes explicit images'                  : 'description1',
            'Content is a threat to spread explicit images'     : 'description2',
        })
    )
    async def sextortype_callback(self, interaction:discord.Interaction, selection:discord.ui.Select):
        tickets[self.tid]['sextortion_content'] = selection.values[0]
        await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)
        await interaction.followup.send('Are these images of you or someone else?', view=ImageOwnerSelection(self.bot, self.tid),  ephemeral=True)

@dataclass
class Option:
        name : str
        callback : callable

# TODO: make this work with labels that aren't yes or no
class YesNoSelection(discord.ui.View):
        def __init__(self, bot, tid : int, opt_1 : Option, opt_2 : Option):
                super().__init__()
                self.tid = tid
                self.bot = bot
                self.opt_1 = opt_1
                self.opt_2 = opt_2

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
        async def Opt1ButtonImpl(self, interaction : discord.Interaction, button : discord.ui.Button):
                await self.opt_1.callback(self.bot, self.tid, interaction, button)

        @discord.ui.button(label="No", style=discord.ButtonStyle.red)
        async def Opt2Button(self, interaction : discord.Interaction, button : discord.ui.Button):
                await self.opt_2.callback(self.bot, self.tid, interaction, button)

# TODO type hints
async def ImageOwnerCallback1(bot, tid, interaction, button):
        tickets[tid]['image_owner'] = 'Me'
        await interaction.response.send_message("Do you know the user responsible?", \
                view=UserResponsibleSelection(bot, tid), ephemeral=True)

# TODO type hints
async def ImageOwnerCallback2(bot, tid, interaction, button):
        tickets[tid]['image_owner'] = 'Other'
        await interaction.response.send_message("Do you know this other person?", \
                view=KnowOtherSelection(bot, tid), ephemeral=True)

def ImageOwnerSelection(bot, tid):
        # This looks shitty because it requires answers to be "yes" or "no"
        return YesNoSelection(
                bot,
                tid, 
                Option("Me", ImageOwnerCallback1),
                Option("Other", ImageOwnerCallback2)
        )

"""
Prompt: "Do you know the user responsible?"
"""
class UserResponsibleSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot

    async def owner_choice_callback(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.response.send_message("Have you shared explicit images with this user?", view=SharedExplicitSelection(self.bot, self.tid), ephemeral=True)
        tickets[self.tid]['know_responsible'] = button.label
        # for key, value in tickets.items():
        #     print(key, value)
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def MeOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await self.owner_choice_callback(interaction, button)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def OtherOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await self.owner_choice_callback(interaction, button)

"""
Prompt: "Have you shared explicit images with this user?"
"""
class SharedExplicitSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def MeOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['shared_explicit'] = 'Yes'
        await interaction.response.send_message("Do you know what images this user has?", view=KnowImageSelection(self.bot, self.tid), ephemeral=True)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def OtherOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['shared_explicit'] = 'No'
        await interaction.response.send_message(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True)

"""
Prompt: "Do you know what images this user has?"
"""
class KnowImageSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot
    
    async def know_image_callback(self, interaction:discord.Interaction, button:discord.ui.Button):
        tickets[self.tid]['know_image'] = button.label
        await interaction.followup.send(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def MeOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await interaction.response.send_message(embed=ImageRemovalEmbed())
        time.sleep(5)
        await self.know_image_callback(interaction, button)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def OtherOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await self.know_image_callback(interaction, button)

"""
Prompt: "Do you know this other person?"
"""
class KnowOtherSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot

    async def know_other_choice_callback(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.followup.send("Did the user post an explicit image?",view=PostExplicitSelection(self.bot, self.tid), ephemeral=True)
        for key, value in tickets.items():
            print(key, value)
        tickets[self.tid]['know_other'] = button.label

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def KnowOtherBtn(self, interaction:discord.Interaction, button:discord.ui.Button):
        UsernameModal = UsernameInputModal(self.tid)
        await interaction.response.send_modal(UsernameModal)
        await UsernameModal.wait()
        await self.know_other_choice_callback(interaction, button)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def DKnowOtherBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await self.know_other_choice_callback(interaction, button)

"""
Prompt: "Do you know this other person?" > "Yes" > "Enter Username"
"""
class UsernameInputModal(discord.ui.Modal, title='Enter Username'):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

        self.value = None

        self.add_item(discord.ui.TextInput(label="Username", style=discord.TextStyle.short))

    async def on_submit(self, interaction: discord.Interaction):
        tickets[self.tid]['other_username'] = self.children[0].value
        await interaction.response.send_message("Thank you!")
        self.stop()

"""
Prompt: "Did the user post an explicit image?"
"""
class PostExplicitSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot
    
    async def post_explicit_callback(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.followup.send(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True)
        tickets[self.tid]['post_explicit'] = button.label

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def MeOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await interaction.response.send_message(embed=ImageRemovalEmbed())
        await self.post_explicit_callback(interaction, button)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def OtherOwnerBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        await self.post_explicit_callback(interaction, button)

"""
Embed to redirect to takeitdown or other external image removal resources
"""
class ImageRemovalEmbed(discord.Embed):
    def __init__(self):
        super().__init__(title='Removal/Preventation Resources', url='https://takeitdown.ncmec.org/')
        self.add_field(name="Please click on the link above.", value="These instructions will help get your image removed and stop their spread", inline=False)
class MainMenuEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.title = "Main Menu Report"
        self.description = "This is the information for the Main Menu"
        self.add_field(name="Report", value="Click this to report", inline=False)
        self.add_field(name="Help", value="Click this to receive more information", inline=False)
        self.add_field(name="Talk to Moderator", value="Click this to request a private conversation with a moderator", inline=False)


class MainMenuButtons(discord.ui.View):
    def __init__(self, bot, mod_channel):
        super().__init__()
        self.bot = bot
        self.mod_channel = mod_channel
        self.add_item(discord.ui.Button(label='Help', style=discord.ButtonStyle.link, url='https://www.stopsextortion.com/get-help/'))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red)
    async def reportBtn(self, interaction: discord.Interaction, button:discord.ui.Button):
        # await interaction.response.send_modal(MyModal())
        tid = uuid.uuid4()
        await interaction.response.send_message(view=ReportSelection(self.bot, tid))
    
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
    
