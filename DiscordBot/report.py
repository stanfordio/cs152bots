from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    REPORT_CANCELLED = auto()
    HARASSMENT_CHOSEN = auto()
    OFFENSIVE_CONTENT_CHOSEN = auto()
    URGENT_VIOLENCE_CHOSEN = auto()
    OTHERS_CHOSEN = auto()
    BLOCK_USER = auto()
    INCITING_VIOLENCE_CHOSEN = auto()
    NOT_IMMEDIATE_DANGER = auto()

class PriorityLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, reporter):
        self.reporter = reporter
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuse_category_message_id = None
        self.block_user_message_id = None
        self.harassment_type_message_id = None
        self.offensive_content_type_message_id = None
        self.inciting_violence_message_id = None
        self.immediate_danger_message_id = None
        self.urgent_violence_category_message_id = None
        self.priority_level = PriorityLevel.LOW
        self.other_explanation = None
        self.final_state = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_CANCELLED
            await message.channel.send("Report cancelled.")
            return
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            await message.channel.send(reply)
            return
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                await message.channel.send("I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel.")
                return
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                await message.channel.send("I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again.")
                return
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                await message.channel.send("It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel.")
                return
            try:
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                await message.channel.send("It seems this message was deleted or never existed. Please try again or say `cancel` to cancel.")
                return

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            sent_message = await message.channel.send(
                f"I found this message:\n"
                f"```{self.message.author.name}: {self.message.content}```\n"
                "Please react with the corresponding number for the reason of your report:\n"
                "1️⃣ - Harassment\n"
                "2️⃣ - Offensive Content\n"
                "3️⃣ - Urgent Violence\n"
                "4️⃣ - Others/I don't like this")
            self.abuse_category_message_id = sent_message.id
            return
        
        if self.state == State.OTHERS_CHOSEN:
            # TODO: Save this message somehow
            self.other_explanation = message.content
            self.final_state = "Others/I don't like this"

            self.state = State.BLOCK_USER
            sent_message = await message.channel.send(
                "Thank you for your report. Would you like to block this user?\n"
                "If so, please react to this message with 👍.\n"
                "Otherwise, react to this message with 👎."
            )
            self.block_user_message_id = sent_message.id
            return
        
        return
    
    async def handle_reaction(self, payload, message):
        if self.state == State.MESSAGE_IDENTIFIED:
            if payload.message_id != self.abuse_category_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣':
                self.state = State.HARASSMENT_CHOSEN
                sent_message = await message.channel.send(
                    "Please react with the corresponding number for which type of harassment you're reporting:\n"
                    "1️⃣ - Trolling\n"
                    "2️⃣ - Impersonation\n"
                    "3️⃣ - Directed Hate Speech\n"
                    "4️⃣ - Doxing\n"
                    "5️⃣ - Unwanted Sexual Content\n")
                self.harassment_type_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣':
                self.state = State.OFFENSIVE_CONTENT_CHOSEN
                sent_message = await message.channel.send(
                    "Please react with the corresponding number for which type of offensive content you're reporting:\n"
                    "1️⃣ - Protected Characteristics (race, color, religion etc.)\n"
                    "2️⃣ - Sexually Graphic Content\n"
                    "3️⃣ - Child Sexual Abuse Material\n"
                    "4️⃣ - Drug Use\n"
                    "5️⃣ - Inciting/Glorifying  Violence\n")
                self.offensive_content_type_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣':
                self.state = State.URGENT_VIOLENCE_CHOSEN
                sent_message = await message.channel.send(
                    "Are you in immediate danger?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.immediate_danger_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣':
                self.state = State.OTHERS_CHOSEN
                await message.channel.send("We're here to help. Can you describe the issue in more detail?")
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, or 4️⃣")
            return
        
        if self.state == State.HARASSMENT_CHOSEN:
            if payload.message_id != self.harassment_type_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣': # Trolling
                self.state = State.BLOCK_USER
                self.final_state = "Trolling"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣': # Impersonation
                self.state = State.BLOCK_USER
                self.final_state = "Impersonation"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣': # Directed Hate Speech
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.MEDIUM
                self.final_state = "Directed Hate Speech"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣': # Doxing
                self.state = State.BLOCK_USER
                self.final_state = "Doxing"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '5️⃣': # Unwanted Sexual Content
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.HIGH
                self.final_state = "Unwanted Sexual Content"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, 4️⃣ or 5️⃣")
            return
        
        if self.state == State.OFFENSIVE_CONTENT_CHOSEN:
            if payload.message_id != self.offensive_content_type_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣': # Protected Characteristics
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.MEDIUM
                self.final_state = "Protected Characteristics"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣': # Sexually Graphic Content
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.MEDIUM
                self.final_state = "Sexually Graphic Content"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣': # Child Sexual Abuse Material
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.HIGH
                self.final_state = "Child Sexual Abuse Material"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣': # Drug Use
                self.state = State.BLOCK_USER
                self.final_state = "Drug Use"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '5️⃣': # Inciting/Glorifying Violence
                self.state = State.INCITING_VIOLENCE_CHOSEN
                sent_message = await message.channel.send(
                    "Please react with the corresponding number for which type of violence you're reporting:\n"
                    "1️⃣ - Dangerous Acts\n"
                    "2️⃣ - Terrorism\n"
                    "3️⃣ - Animal Abuse\n"
                    "4️⃣ - Depiction of Physical Violence\n"
                    "5️⃣ - Other\n"
                )
                self.inciting_violence_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, 4️⃣ or 5️⃣")
            return
        
        if self.state == State.INCITING_VIOLENCE_CHOSEN:
            if payload.message_id != self.inciting_violence_message_id:
                await message.channel.send("Please react to the message that contains emoji options to choose from.")
                return
            
            if str(payload.emoji) == '1️⃣': # Dangerous Acts
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.MEDIUM
                self.final_state = "Inciting/Glorifying Dangerous Acts"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '2️⃣': # Terrorism
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.MEDIUM
                self.final_state = "Inciting/Glorifying Terrorism"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '3️⃣': # Animal Abuse
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.MEDIUM
                self.final_state = "Inciting/Glorifying Animal Abuse"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '4️⃣': # Depiction of Physical Violence
                self.state = State.BLOCK_USER
                self.final_state = "Inciting/Glorifying Physical Violence"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            elif str(payload.emoji) == '5️⃣': # Other
                self.state = State.BLOCK_USER
                self.final_state = "Inciting/Glorifying Violence"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣, 2️⃣, 3️⃣, 4️⃣ or 5️⃣")
            return
        
        if self.state == State.URGENT_VIOLENCE_CHOSEN:
            if payload.message_id != self.immediate_danger_message_id:
                await message.channel.send("Please respond by reacting directly to the block confirmation message above with the appropriate emoji.")
                return
            
            if str(payload.emoji) == '👍':
                self.state = State.REPORT_COMPLETE
                self.priority_level = PriorityLevel.HIGH
                self.final_state = "Immediate Danger"
                await message.channel.send("Please call 911. We will address this report with the highest priority.")
                return
            elif str(payload.emoji) == '👎':
                self.state = State.NOT_IMMEDIATE_DANGER
                sent_message = await message.channel.send(
                    "What category of violence would you classify this as:\n"
                    "1️⃣ - Self Harm\n"
                    "2️⃣ - Directed Threat\n")
                self.urgent_violence_category_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 👍 or 👎")
            return
        
        if self.state == State.NOT_IMMEDIATE_DANGER:
            if payload.message_id != self.urgent_violence_category_message_id:
                await message.channel.send("Please respond by reacting directly to the block confirmation message above with the appropriate emoji.")
                return
            
            if str(payload.emoji) == '1️⃣':
                self.state = State.REPORT_COMPLETE
                self.priority_level = PriorityLevel.HIGH
                self.final_state = "Self Harm"
                await message.channel.send("Thank you for reporting. We will contact local authorities")
                return
            elif str(payload.emoji) == '2️⃣':
                self.state = State.BLOCK_USER
                self.priority_level = PriorityLevel.HIGH
                self.final_state = "Directed Threat"
                sent_message = await message.channel.send(
                    "Thank you for your report. Would you like to block this user?\n"
                    "If so, please react to this message with 👍.\n"
                    "Otherwise, react to this message with 👎."
                )
                self.block_user_message_id = sent_message.id
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 1️⃣ or 2️⃣")
            return

        if self.state == State.BLOCK_USER:
            if payload.message_id != self.block_user_message_id:
                await message.channel.send("Please respond by reacting directly to the block confirmation message above with the appropriate emoji.")
                return
            
            if str(payload.emoji) == '👍':
                self.state = State.REPORT_COMPLETE
                await message.channel.send("You have chosen to block the user, and we have processed your request. We appreciate your help in maintaining a safe community environment.")
                return
            elif str(payload.emoji) == '👎':
                self.state = State.REPORT_COMPLETE
                await message.channel.send("You have chosen not to block the user. We appreciate your help in maintaining a safe community environment.")
                return
            
            await message.channel.send("Sorry, I don't understand what you mean by this emoji. Please react to the previous message with either 👍 or 👎")
            return
        
        return
    
    async def send_report_to_mod_channel(self, mod_channel):
        if self.state != State.REPORT_COMPLETE:
            return

        color_dict = {
            PriorityLevel.LOW: discord.Color.blue(),
            PriorityLevel.MEDIUM: discord.Color.gold(),
            PriorityLevel.HIGH: discord.Color.red()
        }
        color = color_dict.get(self.priority_level, discord.Color.default())

        embed = discord.Embed(
            title="New Report Filed",
            description=f"User {self.reporter.name} filed a report against the following message:",
            color=color
        )
        embed.add_field(name="Message Content", value=f"```{self.message.author.name}: {self.message.content}```", inline=False)
        embed.add_field(name="Priority", value=self.priority_level.value, inline=True)
        embed.add_field(name="Reported by", value=self.reporter.name, inline=True)
        embed.add_field(name="Reported abuse type", value=self.final_state, inline=False)
        if self.other_explanation:
            embed.add_field(name="User explanation", value=self.other_explanation, inline=False)

        await mod_channel.send(embed=embed)


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    def report_cancelled(self):
        return self.state == State.REPORT_CANCELLED
    


    

