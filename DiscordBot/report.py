from enum import Enum, auto
import discord
from discord.ui import Button, View, button, Modal, TextInput
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_REASON = auto()
    AWAITING_HARASSMENT_SUBTYPE = auto()
    AWAITING_REPEATED_BEHAVIOR = auto()
    AWAITING_UNDERSTAND = auto()
    AWAITING_MORE_INFO_CHOICE = auto()
    AWAITING_MORE_INFO = auto()
    AWAITING_SUBMIT = auto()
    AWAITING_BLOCK_CHOICE = auto()
    AWAITING_DANGER_TYPE = auto()
    REPORT_COMPLETE = auto()

class ReportReason(Enum):
    SPAM = "Spam"
    MISINFORMATION = "Misinformation"
    IMPERSONATION = "Impersonation"
    HARASSMENT = "Harassment / Cyber-bullying"
    DANGER = "Imminent Danger / Emergency Situation"

class HarassmentSubType(Enum):
    HATE_SPEECH = "Hate-speech"
    INSULTS = "Insults"
    NON_CONSENSUAL = "Sharing of non-consensual images"
    THREATS = "Threats to user-safety / public intimidation"
    OTHER = "Other"

class DangerType(Enum):
    SUICIDE = "Imminent risk of suicide / suicidal ideation"
    VIOLENCE = "Intent to commit violence"

class AdditionalInfoModal(Modal):
    def __init__(self, report):
        super().__init__(title="Additional Information")
        self.report = report
        
        self.text_input = TextInput(
            label="Additional details:",
            style=discord.TextStyle.paragraph,
            placeholder="Please provide any additional information about this report...",
            required=True,
            max_length=1000
        )
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.report.additional_info = self.text_input.value
        await interaction.response.send_message(
            "Thank you for providing additional information.\n\n"
            "At this moment, would you like to block this user?",
            view=await self.report.create_yes_no_buttons("block")
        )
        self.report.state = State.AWAITING_BLOCK_CHOICE

class MoreInfoView(View):
    def __init__(self, report):
        super().__init__(timeout=300.0)
        self.report = report

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary, custom_id="more_info_yes")
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AdditionalInfoModal(self.report)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="No", style=discord.ButtonStyle.primary, custom_id="more_info_no")
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "At this moment, would you like to block this user?",
            view=await self.report.create_yes_no_buttons("block")
        )
        self.report.state = State.AWAITING_BLOCK_CHOICE

class UnderstandView(View):
    def __init__(self, report):
        super().__init__(timeout=300.0)
        self.report = report

    @discord.ui.button(label="I understand", style=discord.ButtonStyle.primary, custom_id="understand")
    async def understand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Would you like to provide more information?",
            view=MoreInfoView(self.report)
        )
        self.report.state = State.AWAITING_MORE_INFO_CHOICE

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.reported_message = None
        self.reason = None
        self.harassment_subtype = None
        self.is_repeated = None
        self.additional_info = None
        self.danger_type = None

    async def create_reason_buttons(self):
        view = View(timeout=300.0)
        for reason in ReportReason:
            button = Button(
                style=discord.ButtonStyle.primary,
                label=reason.value,
                custom_id=f"reason_{reason.name}"
            )
            button.callback = self.reason_button_callback
            view.add_item(button)
        return view

    async def create_harassment_subtype_buttons(self):
        view = View(timeout=300.0)
        for subtype in HarassmentSubType:
            button = Button(
                style=discord.ButtonStyle.primary,
                label=subtype.value,
                custom_id=f"harass_{subtype.name}"
            )
            button.callback = self.harassment_subtype_callback
            view.add_item(button)
        return view

    async def create_yes_no_buttons(self, custom_id_prefix):
        view = View(timeout=300.0)
        yes_button = Button(
            label="Yes",
            custom_id=f"{custom_id_prefix}_yes",
            style=discord.ButtonStyle.primary
        )
        no_button = Button(
            label="No",
            custom_id=f"{custom_id_prefix}_no",
            style=discord.ButtonStyle.primary
        )
        yes_button.callback = self.yes_no_callback
        no_button.callback = self.yes_no_callback
        view.add_item(yes_button)
        view.add_item(no_button)
        return view

    async def create_understand_button(self):
        return UnderstandView(self)

    async def create_submit_button(self):
        view = View(timeout=300.0)
        button = Button(
            label="Submit",
            custom_id="submit",
            style=discord.ButtonStyle.primary
        )
        button.callback = self.submit_callback
        view.add_item(button)
        return view

    async def create_danger_type_buttons(self):
        view = View(timeout=300.0)
        for dtype in DangerType:
            button = Button(
                style=discord.ButtonStyle.primary,
                label=dtype.value,
                custom_id=f"danger_{dtype.name}"
            )
            button.callback = self.danger_type_callback
            view.add_item(button)
        return view

    async def handle_message(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process.\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            
            try:
                guild = self.client.get_guild(int(m.group(1)))
                channel = guild.get_channel(int(m.group(2)))
                self.reported_message = await channel.fetch_message(int(m.group(3)))
                
                self.state = State.AWAITING_REASON
                view = await self.create_reason_buttons()
                return [("Please select the reason for reporting the message.", view)]
                
            except (discord.NotFound, AttributeError):
                return ["I couldn't find that message. Please try again or say `cancel` to cancel."]

        if self.state == State.AWAITING_MORE_INFO:
            self.additional_info = message.content
            view = await self.create_submit_button()
            return [("Thank you for providing additional information. Click Submit to file your report.", view)]

        return []

    async def reason_button_callback(self, interaction):
        try:
            custom_id = interaction.data['custom_id']
            reason_name = '_'.join(custom_id.split('_')[1:])
            self.reason = ReportReason[reason_name]

            if self.reason in [ReportReason.SPAM, ReportReason.MISINFORMATION, ReportReason.IMPERSONATION]:
                await interaction.response.send_message(
                    "Thank you for notifying us and sending a copy of the message. "
                    "Our team will immediately review the message; the abuser can be warned, muted or removed.\n\n"
                    "At this moment, would you like to block this user?",
                    view=await self.create_yes_no_buttons("block")
                )
                self.state = State.AWAITING_BLOCK_CHOICE

            elif self.reason == ReportReason.HARASSMENT:
                await interaction.response.send_message(
                    "Please select the sub-type.",
                    view=await self.create_harassment_subtype_buttons()
                )
                self.state = State.AWAITING_HARASSMENT_SUBTYPE

            elif self.reason == ReportReason.DANGER:
                await interaction.response.send_message(
                    "Please select the type of danger.",
                    view=await self.create_danger_type_buttons()
                )
                self.state = State.AWAITING_DANGER_TYPE
        except Exception as e:
            print(f"Error in reason_button_callback: {str(e)}")
            await interaction.response.send_message(
                "Sorry, there was an error processing your selection. Please try again.",
                ephemeral=True
            )

    async def harassment_subtype_callback(self, interaction):
        try:
            custom_id = interaction.data['custom_id']
            # The custom_id is in format "harass_HATE_SPEECH", so we need to get everything after "harass_"
            subtype_name = '_'.join(custom_id.split('_')[1:])
            self.harassment_subtype = HarassmentSubType[subtype_name]
            
            await interaction.response.send_message(
                "Is this repeated behaviour?",
                view=await self.create_yes_no_buttons("repeated")
            )
            self.state = State.AWAITING_REPEATED_BEHAVIOR
        except Exception as e:
            print(f"Error in harassment_subtype_callback: {str(e)}")
            await interaction.response.send_message(
                "Sorry, there was an error processing your selection. Please try again.",
                ephemeral=True
            )

    async def yes_no_callback(self, interaction):
        try:
            custom_id = interaction.data['custom_id']
            prefix = custom_id.split('_')[0]
            is_yes = custom_id.endswith('_yes')

            if prefix == "block":
                if is_yes:
                    await interaction.response.send_message(
                        "Thank you; you will no longer receive messages from this user."
                    )
                    # Implement actual blocking here
                else:
                    await interaction.response.send_message(
                        "Thank you for your report. Our team will review it."
                    )
                self.state = State.REPORT_COMPLETE
                await self.send_report()

            elif prefix == "repeated":
                self.is_repeated = is_yes
                if is_yes:
                    await interaction.response.send_message(
                        "We will review the user's activity. If behaviour is deemed repeated and egregious "
                        "we will take more severe action.",
                        view=await self.create_understand_button()
                    )
                    self.state = State.AWAITING_UNDERSTAND
                else:
                    await interaction.response.send_message(
                        "Would you like to provide more information?",
                        view=MoreInfoView(self)
                    )
                    self.state = State.AWAITING_MORE_INFO_CHOICE

        except Exception as e:
            print(f"Error in yes_no_callback: {str(e)}")
            await interaction.response.send_message(
                "Sorry, there was an error processing your selection. Please try again.",
                ephemeral=True
            )

    async def submit_callback(self, interaction):
        await interaction.response.send_message(
            "Thank you for your report. Our team will review it and take appropriate action."
        )
        self.state = State.REPORT_COMPLETE
        await self.send_report()

    async def danger_type_callback(self, interaction):
        try:
            custom_id = interaction.data['custom_id']
            # The custom_id is in format "danger_SUICIDE", so we need to get everything after "danger_"
            dtype_name = '_'.join(custom_id.split('_')[1:])
            self.danger_type = DangerType[dtype_name]
            
            await interaction.response.send_message(
                "Our team will review the message and take the most possible action. "
                "If you are in need of professional help right now, please contact 911 (emergency) "
                "or 988 (US suicide & crisis hotline)."
            )
            self.state = State.REPORT_COMPLETE
            await self.send_report()
        except Exception as e:
            print(f"Error in danger_type_callback: {str(e)}")
            await interaction.response.send_message(
                "Sorry, there was an error processing your selection. Please try again.",
                ephemeral=True
            )

    async def send_report(self):
        mod_channel = self.client.mod_channels.get(self.reported_message.guild.id)
        if not mod_channel:
            return

        embed = discord.Embed(
            title=f"New Report: {self.reason.value}",
            description=f"Message: {self.reported_message.content}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Author", value=self.reported_message.author.name, inline=True)
        embed.add_field(name="Channel", value=self.reported_message.channel.name, inline=True)

        if self.reason == ReportReason.HARASSMENT:
            embed.add_field(name="Harassment Type", value=self.harassment_subtype.value, inline=True)
            embed.add_field(name="Repeated Behavior", value="Yes" if self.is_repeated else "No", inline=True)
            if self.additional_info:
                embed.add_field(name="Additional Information", value=self.additional_info, inline=False)
            embed.color = discord.Color.red()

        elif self.reason == ReportReason.DANGER:
            embed.add_field(name="Danger Type", value=self.danger_type.value, inline=True)
            embed.color = discord.Color.dark_red()
            embed.title = "⚠️ " + embed.title

        await mod_channel.send(embed=embed)

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

