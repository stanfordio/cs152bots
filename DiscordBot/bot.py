# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
import uuid
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

#import apis
from classifiers.gpt import gpt_classify
from classifiers.perspective import perspective_classify
from classifiers.classify import predict_classify

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']

class ReportDatabase:
    def __init__(self):
        self.reports = []
        self.report_log = []
    
    def add_report(self, report):
        self.reports.append(report)

    def add_report_log(self, report):
        self.report_log.append(report)

    def get_next_report(self):
        return self.reports[0]
    
    def remove_report(self, report):
        self.reports.remove(report)

    # create test data all manunual reports
    def create_test_data(self):
        test_user_reports = self.create_test_user_report()
        for i in range(5):
            #Test false reports
            #report = ModeratorReport(0, i+1, "manual", test_user_reports[i])
            report = ModeratorReport(i, i+1, "manual", test_user_reports[i])
            self.add_report(report)

    def create_test_user_report(self):
        result = []
        options = [
            "Sextortion",
            "Sexual Harassment",
            "Child Sexual Exploitation or Abuse",
            "I am a child and someone I don’t know is sending me strange messages",
            "Other"
        ]
        for i in range(5):
            data = {}
            data["Reported User"] = "User" + str(i)
            data["Reported Message"] = "Message" + str(i)
            data ["Abuse Type"] = "Sexual Content and Child Exploitation (I am a child and I feel uncomfortable)"
            data["Abuse Subsection"] = options[i]
            data["Additional Information"] = "Additional Information" + str(i)
            result.append(data)
        return result
    
    
    def report_count(self):
        return len(self.reports)
    
    def check_if_user_has_false_report(self, userID):
        print(self.report_log)
        for report in self.report_log:
            if report.fromUserID == userID and report.fromUserFalseReport:
                return True
        return False
    
class ModeratorReport:
    def __init__(self, fromUserID, againstUserID, reportMethod, userReport=None):
        self.id = uuid.uuid4()
        self.fromUserID = fromUserID
        self.againstUserID = againstUserID
        self.reportMethod = reportMethod
        self.abuseType = None
        self.status = "pending"
        self.immediateDanger = None
        self.timestamp = None
        self.priorityType = None
        self.serverity = None
        self.userReport = userReport
        self.fromUserFalseReport = False

    def assign_serverity(self, serverity):
        self.serverity = serverity

    def assign_id(self, id):
        self.id = id

    def assign_timestamp(self, timestamp):
        self.timestamp = timestamp

    def assign_status(self, status):
        self.status = status

    def assign_serverity(self, serverity):
        self.serverity = serverity

    def assign_priorityType(self, priorityType):
        self.priorityType = priorityType

    def assign_immediateDanger(self, immediateDanger):
        self.immediateDanger = immediateDanger

    def assign_reportMethod(self, reportMethod):
        self.reportMethod = reportMethod

    def assign_abuseType(self, abuseType):
        self.abuseType = abuseType

    def format_user_report(self):
        report = self.userReport
        user_report = ""
        for key, value in report.items():
            user_report += f'{key}: {value} \n'
        return user_report

    def __repr__(self):
        return f'ModeratorReport(id={self.id}, fromUserID={self.fromUserID}, againstUserID={self.againstUserID}, reportMethod={self.reportMethod}, abuseType={self.abuseType}, status={self.status}, immediateDanger={self.immediateDanger}, timestamp={self.timestamp}, priorityType={self.priorityType}, serverity={self.serverity})'



class IssueQueue:
    def __init__(self):
        self.high_priorty = []
        self.low_priority = []
        
    def add_report(self, report):
        if report.priorityType == "low":
            self.low_priority.append(report)
        else:
            self.high_priorty.append(report)

    def peek_report(self):
        if len(self.high_priorty) == 0 and len(self.low_priority) == 0:
            print("No reports in queue")
            return None
        if len(self.high_priorty) == 0:
            return self.low_priority[0]
        else:
            return self.high_priorty[0]

    def remove_report(self, issue):
        if issue.priorityType == "low":
            return self.low_priority.remove(issue)
        else:
            return self.high_priorty.remove(issue)
    
    def queue_count(self):  
        return len(self.high_priorty) + len(self.low_priority)



async def handle_mod_response(self, message, mod_channel):
    # System is not waiting for a response from the user
    if not_waiting_for_response(self):
        if message.content == "load test":
            await mod_channel.send(f'System: Loading test data')
            self.report_database.create_test_data()
            await mod_channel.send(f'System: {self.report_database.report_count()} reports loaded in Database')
            await status_message(self, mod_channel)
    
        if message.content == "help" or message.content == "status":
            await status_message(self, mod_channel)

        if message.content == "1":
            # First time user presses start processing report
            await mod_channel.send(f'System: Processing pending reports')
            await proccess_pending_reports(self, mod_channel, message)
            
        if message.content == "2":
            # First time user presses to handle issues
            await mod_channel.send(f'System: Addressing issues')
            await address_issues(self, mod_channel, message)
    
    # System is waiting for a response from the user
    else:
        if self.processing_report_state != -1:
            await proccess_pending_reports(self, mod_channel, message)
        if self.addressing_issues_state != -1:
            await address_issues(self, mod_channel, message)



async def proccess_pending_reports(self, mod_channel, message):
    report = self.report_database.get_next_report()

    # First time user presses start processing report
    if self.processing_report_state == -1:
        await mod_channel.send(f'System: Processing report {report.id}')
        await mod_channel.send(f'_________________________________________________________')
        await mod_channel.send(f'User Report:')
        await mod_channel.send(f'From UserID: {report.fromUserID}')
        await mod_channel.send(f'User Report: {report.format_user_report()} \n')
        await mod_channel.send(f'_________________________________________________________')
        await mod_channel.send(f'Is this report related to sexual content or child exploitation? (yes/no)')
        self.processing_report_state = 0
    
    # User has already started processing report, asking if report is related to sexual content or child exploitation
    elif self.processing_report_state == 0:
        if message.content.lower() == "yes":
            self.processing_report_state = 2
            await mod_channel.send(f'Please classify the report as sextortion, sexual harassment, or child exploitation. \n 1) sextortion 2) sexual harassment 3) child exploitation')
        elif message.content.lower() == "no":
            self.processing_report_state = 1
            await mod_channel.send(f'Is the user in immediate danger? (yes/no)')

    # User has already started processing report, asking if user is in immediate danger
    elif self.processing_report_state == 1:
        if message.content.lower() == "yes":
            self.processing_report_state = 2
            report.assign_immediateDanger(True)
            await mod_channel.send(f'System: Immediate danger set to True')
            await mod_channel.send(f'Please classify the report as sextortion, sexual harassment, or child exploitation. \n 1) sextortion 2) sexual harassment 3) child exploitation')
        elif message.content.lower() == "no":
            self.processing_report_state = 2
            report.assign_immediateDanger(False)
            await mod_channel.send(f'System: Immediate danger set to False')
            report.assign_priorityType("low")
            await mod_channel.send(f'System: Priority set to low')
            self.issue_queue.add_report(report)
            report.assign_status("in_progress")
            self.report_database.remove_report(report)
            await mod_channel.send(f'System: Report {report.id} added to issue queue')
            # send database and issue queue size then add line break
            await mod_channel.send(f'System: {self.report_database.report_count()} reports in Database \n {self.issue_queue.queue_count()} issues in Queue')
            await mod_channel.send(f'_________________________________________________________')
            self.processing_report_state = -1
            await status_message(self, mod_channel)

    # User has already started processing report, asking for abuse type
    elif self.processing_report_state == 2:
        if message.content == "1":
            report.assign_abuseType("sextortion")
            await mod_channel.send(f'System: Abuse type set to sextortion')
        elif message.content == "2":
            report.assign_abuseType("sexual harassment")
            await mod_channel.send(f'System: Abuse type set to sexual harassment')
        elif message.content == "3":
            report.assign_abuseType("child exploitation")
            await mod_channel.send(f'System: Abuse type set to child exploitation')
        self.processing_report_state = 3
        report.assign_priorityType("high")
        await mod_channel.send(f'System: Priority set to high')
        self.issue_queue.add_report(report)
        report.assign_status("in_progress")
        self.report_database.remove_report(report)
        await mod_channel.send(f'System: Report {report.id} added to issue queue')  
        # send database and issue queue size then add line break
        await mod_channel.send(f'_________________________________________________________')
        self.processing_report_state = -1
        await status_message(self, mod_channel)

async def address_issues(self, mod_channel, message): 
    report = self.issue_queue.peek_report()

    # First time user presses start processing report
    if self.addressing_issues_state == -1:
        await mod_channel.send(f'System: Addressing issue {report.id}')
        await mod_channel.send(f'_________________________________________________________')
        await mod_channel.send(f'User Report:')
        await mod_channel.send(f'From UserID: {report.fromUserID}')
        await mod_channel.send(f'User Report: {report.format_user_report()} \n')
        await mod_channel.send(f'_________________________________________________________')
        await mod_channel.send(f'Please classify the serverity of the issue \n 1) low 2) medium 3) high 4) critical')
        self.addressing_issues_state = 0
    
    # User has already started processing report, asking for serverity
    elif self.addressing_issues_state == 0:
        if message.content == "1":
            report.assign_serverity(1)
            await mod_channel.send(f'System: Serverity set to low')
            await mod_channel.send(f'Is this a false report? (yes/no)')
            self.addressing_issues_state = 1
            return
        elif message.content == "2":
            report.assign_serverity(2)
            await mod_channel.send(f'System: Serverity set to medium')
            await delete_chat_history(self, report, mod_channel)
            await warn_user(self, report, mod_channel)
        elif message.content == "3":
            report.assign_serverity(3)
            await mod_channel.send(f'System: Serverity set to high')
            await delete_chat_history(self, report, mod_channel)
            await issue_suspension(self, report, mod_channel)
        elif message.content == "4":
            report.assign_serverity(4)
            await mod_channel.send(f'System: Serverity set to critical')
            await delete_chat_history(self, report, mod_channel)
            await ban_user(self, report, mod_channel)

        if self.addressing_issues_state != 1:
            self.report_database.add_report_log(report)
            await mod_channel.send(f'System: Report {report.id} removed from issue queue')
            self.addressing_issues_state = -1
            self.issue_queue.remove_report(report)
            await mod_channel.send(f'_________________________________________________________')
            await status_message(self, mod_channel)


    # User has already started processing report, asking for false report
    elif self.addressing_issues_state == 1:
        if message.content.lower() == "yes":
            report.assign_status("resolved")
            report.fromUserFalseReport = True
            if self.report_database.check_if_user_has_false_report(report.fromUserID):
                await ban_user(self, report, mod_channel, report.fromUserFalseReport)
            else:
                await warn_user(self, report, mod_channel, report.fromUserFalseReport)
            await mod_channel.send(f'System: Report {report.id} marked as resolved')
            await mod_channel.send(f'System: Report {report.id} removed from issue queue')
            # send size of issue queue then add line break
            await mod_channel.send(f'_________________________________________________________')
            self.report_database.add_report_log(report)
            self.issue_queue.remove_report(report)
            self.addressing_issues_state = -1
            await status_message(self, mod_channel)

        elif message.content.lower() == "no":
            report.assign_status("resolved")
            await warn_user(self, report, mod_channel)
            await mod_channel.send(f'System: Report {report.id} marked as resolved')
            await mod_channel.send(f'System: Report {report.id} removed from issue queue')
            # send size of issue queue then add line break
            await mod_channel.send(f'_________________________________________________________')
            self.report_database.add_report_log(report)
            self.issue_queue.remove_report(report)
            self.addressing_issues_state = -1
            await status_message(self, mod_channel)

async def issue_suspension(self, report, mod_channel):
    # issue suspension
    await mod_channel.send(f'System: User {report.againstUserID} suspended')

async def delete_chat_history(self, report, mod_channel):
    # delete chat history
    await mod_channel.send(f'System: Chat history deleted for user {report.againstUserID}')

async def ban_user(self, report, mod_channel, false_report=False):
    # ban user
    if false_report:
        await mod_channel.send(f'System: User {report.fromUserID} banned for false report')
    else:
        await mod_channel.send(f'System: User {report.againstUserID} banned')

async def warn_user(self, report, mod_channel, false_report=False):
    # warn user
    if false_report:
        await mod_channel.send(f'System: User {report.fromUserID} warned for false report')
    else:
        await mod_channel.send(f'System: User {report.againstUserID} warned')

async def status_message(self, mod_channel):
    await mod_channel.send(
        f"""
        System: \n 
        {self.report_database.report_count()} reports in Database \n 
        {self.issue_queue.queue_count()} issues in Queue \n 
        Press: \n 
            1) Process Pending Reports \n 
            2) Address Queued Issues
        """)


def not_waiting_for_response(self):
    if self.processing_report_state == -1:
        if self.addressing_issues_state == -1:
            return True
    return False
class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.report_database = ReportDatabase()
        self.issue_queue = IssueQueue()

        # Process Pending Report States
        #  -1) show user report
        #   0) awaiting response for sexual content and child exploitation
        #   1) awaiting response for immediate danger
        #   2) awaiting response for type of abuse
        self.processing_report_state = -1
        
        # Process Addressing Issues States
        #  -1) show user report
        #   0) awaiting response for serverity
        #   1) awaiting response for false report
        self.addressing_issues_state = -1

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)
            if "Thank you for submitting a report" in r:
                new_report = ModeratorReport(author_id, self.reports[author_id].result["Reported User"], "manual", self.reports[author_id].result)
                #new_report = ModeratorReport("thecoolsaraa123", "rickzipper234", "manual", self.reports[author_id].result)
                self.report_database.add_report(new_report)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}' and not message.channel.name == f'group-{self.group_num}-mod':
            return
        
        mod_channel = self.mod_channels[message.guild.id]
        if message.channel.name == f'group-{self.group_num}-mod':
            # Process messages within moderator 
            await handle_mod_response(self, message, mod_channel)
            return

        # Forward the message to the mod channel
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        severity = self.calculate_severity(*scores)
        await mod_channel.send(self.code_format(message.content, severity))

    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''

        # Sample messages and their true labels
        messages = [
            ("Hello, how are you today?", "None"),
            ("A: did u eat supper yet\nB: yeah I ordered papa johns pizza and u baby\nA: gonna go eat now\nB: will u b on later\nA: okay babby what u eating", "Mild"),
            ("rickzipper234: Hey thecoolsaraa123, you're doing great at this game! How old are you? I'm curious because you're so good.\nthecoolsaraa123: I’m 13. Thanks for saying that!\nrickzipper234: That's awesome. You seem really mature for your age. Do you like getting special gifts?\nthecoolsaraa123: I guess so. What kind of gifts?\nrickzipper234: I could send you some in-game credits or even real presents. How about that?\nthecoolsaraa123: Sounds cool! How do I get them?\nrickzipper234: I’d love to send them to you, but maybe we could exchange something. Could you send me some nice photos?\nthecoolsaraa123: What kind of photos?\nrickzipper234: Just some that show how cute you are. No big deal. It’ll be our little secret.\nthecoolsaraa123: I don’t know. I don’t usually share photos.\nrickzipper234: It’s nothing to worry about! If you trust me, I promise I’ll keep your pictures safe. You’ll get something great in return.\nthecoolsaraa123: I’m not sure this is okay…\nrickzipper234: Come on, just a few photos. Friends trust each other. And remember, you’re getting cool stuff.\nthecoolsaraa123: I don’t feel good about.", "Severe"),
            ("hey babe been thinking about you", "Moderate"),
            ("You look beautiful today baby. Could I get some pictures?", "Moderate"),
            ("Do you want to get some food?", "None"),
            ("A: I’m 13\nB: Could you send some pictures?", "Moderate"),
            ("Hey are you free later tonight? So we can spend some time just the two of us?", "Mild"),
            ("You’re really mature for your age. You don’t seem 14.", "Mild"),
            ("I know you’re 12, but that doesn’t mean I don’t want to see your body.", "Severe"),
        ]

        gpt_score = gpt_classify(message)
        perspective_score = perspective_classify(message)
        naive_bayes_score, logistic_reg_score = predict_classify(message)
        
        print('gpt_score: ', gpt_score)
        print('perspective_score: ', perspective_score)
        print('naive_bayes_score: ', naive_bayes_score)
        print('logistic_reg_score: ', logistic_reg_score)

        # true_labels = [label for _, label in messages]
        # predicted_labels = [gpt_classify(message) for message, _ in messages]

        # # Generate confusion matrix
        # cm = confusion_matrix(true_labels, predicted_labels, labels=['None', 'Mild', 'Moderate', 'Severe'])

        # # Display confusion matrix
        # disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['None', 'Mild', 'Moderate', 'Severe'])
        # disp.plot(cmap=plt.cm.Blues)
        # plt.title('Confusion Matrix')
        # plt.show()

        return gpt_score, perspective_score, naive_bayes_score, logistic_reg_score


    def calculate_severity(self, gpt_score, perspective_score, naive_bayes_score, logistic_reg_score):
        if (naive_bayes_score == 0 and logistic_reg_score == 0):
            if gpt_score == 'None':
                return 1
            if gpt_score == 'Mild':
                return 2
            # if gpt_score  == 'Moderate' or perspective_score < 0.6:
            #     return 3
            return 3
        
        if ((naive_bayes_score == 0 and logistic_reg_score == 1) or (naive_bayes_score == 1 and logistic_reg_score == 0)):
            if gpt_score == 'None' or gpt_score == 'Mild':
                return 2
            if gpt_score  == 'Moderate' and (perspective_score < 0.6 and perspective_score > 0.1): 
                return 3
            return 4
        
        if (naive_bayes_score == 1 and logistic_reg_score == 1):
            if gpt_score == 'None' or gpt_score == 'Mild' or gpt_score  == 'Moderate':
                return 3
            return 4
        return 1 # technically shouldn't ever get here/run

    
    def code_format(self, message, severity):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + message + "' with Severity " + str(severity)


client = ModBot()
client.run(discord_token)
