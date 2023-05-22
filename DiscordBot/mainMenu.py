import discord
from myModal import MyModal
import uuid
import time

tickets = {}

def get_drop_down_options(elems : dict[str, str]) -> list[discord.SelectOption]:
        return [discord.SelectOption(label=l, description=d) for l, d in elems.items()]

async def send_completionEmbed(interaction, bot, tid):
    await interaction.followup.send(embed=await create_completionEmbed(bot, tid))

    mod_channel = bot.mod_channels[bot.guilds[0].id]
    embed = await create_completionEmbed(bot, tid)
    embed.title = f"Report Ticket ID: {tid}"
    embed.description = None
    await mod_channel.send(embed=embed)


async def create_completionEmbed(bot, tid):
    embed = CompletionEmbed(bot, tid)

    if 'message_link' in tickets[tid].keys():
        # link = 'https://discord.com/channels/1103033282779676743/1103033287250804838/1109919564701126787'
        link = tickets[tid]['message_link'].split('/')
        try:
            # FIXME This indexes out of bounds.
            message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(int(link[-1]))
            tickets[tid]['message'] = message.content
            tickets[tid]['msg_user_id'] = message.author
        except:
            message = 'Could not identify.'

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
        self.add_field(name='Status', value='In Progress', inline=False)

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

        tickets[self.tid] = {'user_id_requester' : interaction.user, 'reason': selection.values[0]}
        reason = ExplanationModal(selection.values[0], self.tid)
        await interaction.response.send_modal(reason)
        await reason.wait()
        time.sleep(1)

        if selection.values[0] == 'Harassment':
            await interaction.followup.send("You selected: Harassment", view=HarassmentSelection(self.bot, self.tid), ephemeral=True)
        else:
            await send_completionEmbed(interaction, self.bot, self.tid)


class ExplanationModal(discord.ui.Modal):
    def __init__(self, choice, tid):
        super().__init__(title=f"Your report reasoning is: {choice}")
        self.tid = tid

        self.add_item(discord.ui.TextInput(label="Paste Message Link ", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="Please explain your reasoning", style=discord.TextStyle.long))

    async def on_submit(self, interaction: discord.Interaction):
        tickets[self.tid]['message_link'] = self.children[0].value
        tickets[self.tid]['reason'] = self.children[1].value
        await interaction.response.send_message("Thank you for your response!", ephemeral=True)
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

        await interaction.response.send_message(f'You responded: {selection.values[0]}',  ephemeral=True)

        if selection.values[0] == 'Sextortion':
            await interaction.followup.send(view=SextortionTypeSelection(self.bot, self.tid),  ephemeral=True)
        else:
            await send_completionEmbed(interaction, self.bot, self.tid)


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
        await interaction.response.send_message(f'You responded: {selection.values[0]}',  ephemeral=True)
        await interaction.followup.send('Are these images of you or someone else?', view=ImageOwnerSelection(self.bot, self.tid),  ephemeral=True)

# =========== TYPE ALIASES ==============
Interaction = discord.Interaction
Button = discord.ui.Button
# ========= END TYPE ALIASES ===========

def BinaryOption(label_1 : str, label_2 : str):
        class Impl(discord.ui.View):
                # TODO: tighten up argument types on these callables
                def __init__(self, bot, tid : int, opt_1 : callable, opt_2 : callable):
                        super().__init__()
                        self.tid = tid
                        self.bot = bot
                        self.opt_1 = opt_1
                        self.opt_2 = opt_2

                @discord.ui.button(label=label_1, style=discord.ButtonStyle.red)
                async def Opt1Button(self, interaction : discord.Interaction, button : discord.ui.Button):
                        await self.opt_1(self.bot, self.tid, interaction, button)

                @discord.ui.button(label=label_2, style=discord.ButtonStyle.red)
                async def Opt2Button(self, interaction : discord.Interaction, button : discord.ui.Button):
                        await self.opt_2(self.bot, self.tid, interaction, button)

        return Impl

# =========== TYPE ALIASES ==============
YesNoOption = BinaryOption("Yes", "No")
# ========= END TYPE ALIASES ===========

# TODO type hints
async def ImageOwnerCallback1(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid]['image_owner'] = 'Me'
        await interaction.response.send_message(f'You responded: {button.label}', ephemeral=True)
        await interaction.followup.send("Do you know the user responsible?",
                view=UserResponsibleSelection(bot, tid), ephemeral=True)

# TODO type hints
async def ImageOwnerCallback2(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid]['image_owner'] = 'Other'
        await interaction.response.send_message(f'You responded: {button.label}')
        await interaction.followup.send("Do you know this other person?", 
        view=KnowOtherSelection(bot, tid), ephemeral=True)

"""
Prompt: Are these images of you or someone else?
"""
def ImageOwnerSelection(bot, tid : int):
        return BinaryOption("Me", "Other")(bot, tid, ImageOwnerCallback1, ImageOwnerCallback2)

async def owner_choice_callback(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message(f'You responded: {button.label}',  ephemeral=True)
        await interaction.followup.send("Have you shared explicit images with this user?",
                view=SharedExplicitSelection(bot, tid), ephemeral=True)
        tickets[tid]['know_responsible'] = button.label

"""
Prompt: Do you know this other person?
"""
def UserResponsibleSelection(bot, tid : int):
        return YesNoOption(bot, tid, owner_choice_callback, owner_choice_callback)

async def my_images_callback(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid]['shared_explicit'] = 'Yes'
        await interaction.response.send_message('You responded: Yes.',  ephemeral=True)
        await interaction.followup.send("Do you know what images this user has?",
                view=KnowImageSelection(bot, tid), ephemeral=True)

async def others_images_callback(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid]['shared_explicit'] = 'No'
        # await interaction.response.send_message(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True)
        await interaction.response.send_message('You responded: No.',  ephemeral=True)
        await send_completionEmbed(interaction, bot, tid)

"""
Prompt: "Have you shared explicit images with this user?"
"""
def SharedExplicitSelection(bot, tid : int):
        return YesNoOption(bot, tid, my_images_callback, others_images_callback)

async def know_image_callback(bot, tid : int, interaction:Interaction, button:Button):
        tickets[tid]['know_image'] = button.label
        await send_completionEmbed(interaction, bot, tid)

async def handle_know_image(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message('You responded: Yes.', embed=ImageRemovalEmbed())
        time.sleep(5)
        await know_image_callback(bot, tid, interaction, button)

async def handle_dont_know_image(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message('You responded: No.', ephemeral=True)
        await know_image_callback(bot, tid, interaction, button)

"""
Prompt: "Do you know what images this user has?"
"""
def KnowImageSelection(bot, tid : int):
        return YesNoOption(bot, tid, handle_know_image, handle_dont_know_image)

async def know_other_choice_callback(bot, tid : int, interaction:Interaction, button:Button):
        await interaction.followup.send("Did the user post an explicit image?",
                view=PostExplicitSelection(bot, tid), ephemeral=True)
        tickets[tid]['know_other'] = button.label

async def handle_know_other(bot, tid : int, interaction : Interaction, button : Button):
        UsernameModal = UsernameInputModal(tid)
        await interaction.response.send_modal(UsernameModal)
        await UsernameModal.wait()
        await know_other_choice_callback(bot, tid, interaction, button)

async def handle_dont_know_other(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message("You responded: No.", ephemeral=True)
        await know_other_choice_callback(bot, tid, interaction, button)
        
"""
Prompt: "Do you know this other person?"
"""
def KnowOtherSelection(bot, tid : int):
        return YesNoOption(bot, tid, handle_know_other, handle_dont_know_other)

"""
Prompt: "Do you know this other person?" > "Yes" > "Enter Username"
"""
class UsernameInputModal(discord.ui.Modal, title='Enter Username'):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

        self.value = None

        self.add_item(discord.ui.TextInput(label="Username", style=discord.TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        tickets[self.tid]['other_username'] = self.children[0].value
        await interaction.response.send_message("Thank you for filling out the form!", ephemeral=True)
        self.stop()

async def post_explicit_callback(bot, tid : int, interaction : Interaction, button : Button):
        await send_completionEmbed(interaction, bot, tid)
        tickets[tid]['post_explicit'] = button.label

async def handle_post_explicit(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message('You responded: Yes.', embed=ImageRemovalEmbed(),
                ephemeral=True)
        await post_explicit_callback(bot, tid, interaction, button)

async def handle_didnt_post_explicit(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message('You responded: No.',  ephemeral=True)
        await post_explicit_callback(bot, tid, interaction, button)

"""
Prompt: "Did the user post an explicit image?"
"""
def PostExplicitSelection(bot, tid : int):
        return YesNoOption(bot, tid, handle_post_explicit, handle_didnt_post_explicit)

"""
Embed to redirect to takeitdown or other external image removal resources
"""
class ImageRemovalEmbed(discord.Embed):
    def __init__(self):
        super().__init__(title='Removal/Prevention Resources', url='https://takeitdown.ncmec.org/')
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
        self.add_item(Button(label='Help', style=discord.ButtonStyle.link, url='https://www.stopsextortion.com/get-help/'))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red)
    async def reportBtn(self, interaction: Interaction, button:Button):
        # await interaction.response.send_modal(MyModal())
        tid = uuid.uuid4()
        await interaction.response.send_message(view=ReportSelection(self.bot, tid))
    
    # @discord.ui.button(label="Help", style=discord.ButtonStyle.red)
    # async def helpBtn(self, interaction: Interaction, button:Button):
    #     await self.mod_channel.send(f'Forwarded message:\n{interaction.user.display_name}: Help!')
    #     await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)

    @discord.ui.button(label="Talk to Mod", style=discord.ButtonStyle.red)
    async def talkBtn(self, interaction: Interaction, button:Button):
        await self.mod_channel.send(f'Forwarded message:\n{interaction.user.display_name}: Help!')
        await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)

	# async def reportBtn(self, interaction: Interaction, button:Button):
    #     await interaction.response.send_modal(MyModal())
    
