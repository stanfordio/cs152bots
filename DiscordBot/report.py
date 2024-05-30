from enum import Enum, auto
import discord
import re
from deep_translator import GoogleTranslator
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
import os
from dotenv import load_dotenv

#Todo import our new classifier

load_dotenv()

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    SELECT_TYPE = auto()
    SUB_TYPE = auto()
    REPORT_SUBMITTED = auto()
    ASK_BLOCK_USER = auto()
    FINAL_MESSAGE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_type = None
        self.sub_type = None
        self.reported_message = None
        self.translator = GoogleTranslator(source='auto', target='en')
        #instantiate our new classifier in the object.

        self.endpoint = os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")
        self.key = os.getenv("AZURE_TEXT_ANALYTICS_KEY")
        self.text_analytics_client = TextAnalyticsClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    async def handle_message(self, message, mod_channel):
        '''
        This function manages the state transitions and user interactions for the reporting process in a Discord bot.
        '''
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.FINAL_MESSAGE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. Say `help` at any time for more information.\n\n"
            reply += "Please copy and paste the link to the message you want to report."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["Invalid link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I'm not in the reported guild. Please add me and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["Channel not found. Please try again or say `cancel` to cancel."]
            try:
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["Message not found. Please try again or say `cancel` to cancel."]
            
            self.state = State.SELECT_TYPE
            self.reported_message = self.message
            
            self.reported_message.content = self.translator.translate(self.reported_message.content)
        
            
            #TODO Chloe and Tish input in your classifier here
            issues = self.classify_message(self.reported_message.content)
            if issues:
                await self.send_to_mod_channel(self.reported_message.content, issues, mod_channel)
                return ["Message found:", f"```{self.message.author.name}: {self.reported_message.content}```",
                        "The message has been classified with issues. Our moderation team has been notified."]
            else:
                return ["Message found:", f"```{self.message.author.name}: {self.reported_message.content}```",
                        "Please select the type of issue:",
                        "1. Harassment  2. Offensive Content  3. Spam  4. Imminent Danger"]

        if self.state == State.SELECT_TYPE:
            if message.content.isdigit() and 1 <= int(message.content) <= 4:
                self.report_type = int(message.content)
                reply = ["Please specify:"]
                if self.report_type == 1:
                    reply.append("1. Bullying  2. Stalking  3. Doxxing  4. Backlash")
                elif self.report_type == 2:
                    reply.append("1. Hate speech  2. Sexually explicit content  3. Child abuse  4. Extremist content")
                elif self.report_type == 3:
                    reply.append("1. Misinformation  2. Fraud/Extortion  3. Impersonation")
                elif self.report_type == 4:
                    reply.append("1. Credible threat  2. Violence  3. Self harm")
                self.state = State.SUB_TYPE
                return reply
            else:
                return ["Invalid selection. Please try again."]
        
        if self.state == State.SUB_TYPE:
            if message.content.isdigit() and 1 <= int(message.content) <= 4:
                self.sub_type = int(message.content)
                self.state = State.REPORT_SUBMITTED
                response = ["Thank you for reporting this message."]
                if self.report_type == 4:  # Imminent Danger
                    response.append("Our content moderation team will review this message and take the appropriate actions moving forward. This may include contacting law enforcement and removing the user from our platform.")
                else:
                    response.append("Our content moderation team will review this message and take the appropriate actions, which may include removing this user from our platform.")
                response.append("Would you like to block this user? This will prevent them from sending you messages in the future.")
                self.state = State.ASK_BLOCK_USER
                return response
            else:
                return ["Invalid subtype selected. Please try again or say `cancel` to cancel."]
        
        if self.state == State.ASK_BLOCK_USER:
            # Logic to handle user's choice about blocking could be implemented here.
            self.state = State.FINAL_MESSAGE
            
            # Logic to handle forwarding report to mod channel
            await mod_channel.send(f'ALERT: A message has been reported. \n{self.reported_message.author.name}: "{self.reported_message.content}"')
            return ["Thanks for your response. We'll take it from here!"]

        if self.state == State.FINAL_MESSAGE:
            return ["Thank you!"]
        
        return []

    def report_complete(self):
        return self.state == State.FINAL_MESSAGE

    def classify_message(self, message_content):
        print("Classifying message:", message_content)
        try:
            poller = self.text_analytics_client.begin_analyze(
                documents=[{"id": "1", "text": message_content}],
                actions=[{"action_type": "singleCategoryClassify", "project_name": "<your_project_name>", "deployment_name": "<your_deployment_name>"}]
            )
            result = poller.result()
            if "singleCategoryClassify" in result:
                classification_result = result["singleCategoryClassify"][0]
                if classification_result["error"] is not None:
                    return ["Error occurred during classification: " + classification_result["error"]["message"]]
                else:
                    category = classification_result["category"]
                    confidence_score = classification_result["confidenceScore"]
                    print(f"Message: {message_content}")
                    print(f"Classified as: '{category}' with confidence score {confidence_score}")
                    return [f"Message classified as '{category}' with confidence score {confidence_score}"]
            else:
                return ["Classification not available"]
        except Exception as e:
            return ["Error occurred during classification: " + str(e)]


    async def send_to_mod_channel(self, content, issues, mod_channel):
        await mod_channel.send(f'ALERT: Issues detected in reported message: {content}\nIssues: {issues}')


        