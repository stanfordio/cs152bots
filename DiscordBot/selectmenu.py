import discord

class MainMenu(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
    
    @discord.