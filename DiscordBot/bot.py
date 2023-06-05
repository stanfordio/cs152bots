# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from itertools import count
import openai
openai.organization = "org-YVZe9QFuR0Ke0J0rqr7l2R2L"

# from DiscordBot import mod_flow
from report import Report, BotReactMessage
import pdb
from queue import PriorityQueue
# from mod_flow import new_report

# Stuff from mod_flow

####################################################################################################

HIGHEST_PRI = 1
HIGH_PRI = 2
MED_PRI = 3
LOW_PRI = 4

def new_report(completed_report, user_being_reported, user_making_report, reports_by_user, reports_about_user):

    # Check abuse type
    reported_issues = completed_report.get_reported_issues()
    decisions = []

    if Report.HARASSMENT in reported_issues:
        decisions.append(harassment_report(user_being_reported, reports_about_user))
    elif Report.SPAM in reported_issues:
        decisions.append(spam_report(reports_about_user[user_being_reported]))
    elif  Report.THREAT in reported_issues[0]:
        decisions.append(threat_report(completed_report))
    elif Report.FRAUD in reported_issues[0]:
        decisions.append(fraud_report(completed_report))
    else:  # Other
        decisions.append(other_report(completed_report))

    # pick most important decision:
    final_decision, final_message, final_pri = "NO_ACTION", "", LOW_PRI
    for decision in decisions:
        d, m, p = decision
        if d == "BAN" and final_decision != "BAN":
             final_decision, final_message, final_pri = d, m, p
        elif d == "SUSPEND" and (final_decision == "NO_ACTION" or final_decision == "MANUAL"):
             final_decision, final_message, final_pri = d, m, p
        elif d == "MANUAL" and final_decision == "MANUAL":
             final_decision, final_message, final_pri = d, m, p
        if d == final_decision and p < final_pri:
             final_decision, final_message, final_pri = d, m, p

    return final_decision, final_message, final_pri


def harassment_report(completed_report, list_of_reports_against_user):
    is_harrassment = spam(completed_report.get_reported_message())

    harrassment_count = 0
    for report in list_of_reports_against_user:
        if Report.HARASSMENT in report.reported_issues:
            harrassment_count += 1

    if is_harrassment and harrassment_count < 3:
        'SUSPEND', "Your message was marked as harmful, you have been suspended " \
                          "for 15 days. Please contact us if you think we made a mistake.", MED_PRI
    elif harrassment_count >= 3 and is_harrassment:  # many reports of harassment
        return 'BAN', "Your account has been banned due to too many harmful messages.", MED_PRI
    elif harrassment_count > 5:  # many reports of harassment
        return 'SUSPEND', "You have been suspended for 15 days due to harmful messages. Please contact us if you think we made a mistake.", MED_PRI
    else:
        return  "MANUAL", "", MED_PRI


def spam_report(completed_report, list_of_reports_against_user):
    spam_count = 0
    is_spam = spam(completed_report.get_reported_message())
    for report in list_of_reports_against_user:
        if  Report.SPAM in report.reported_issues[0]:
            spam_count += 1

    if is_spam and spam_count >= 3:  # user has been reported many times for spam
        return 'BAN', "Your account has been banned due to too many spam messages.", MED_PRI
    elif is_spam and spam_count < 3:
        return 'SUSPEND', "Your account has been suspended due to reports of spam messages. ", MED_PRI
    else:
        return 'NO ACTION', ": We did not find this message to be abusive. " \
                          "Please contact us if you think we made a mistake.", LOW_PRI


def threat_report(completed_report):
    is_threat = threat(completed_report.get_reported_message)
    if is_threat:
        return 'BAN', "Your account has been banned due to harmful messages.", HIGH_PRI
    return 'MANUAL', "", HIGHEST_PRI


def fraud_report(completed_report):
    reported_issues = completed_report.get_reported_issues()

    if Report.REQUESTED_MONEY in reported_issues:
        # if Report.OBTAINED_MONEY in reported_issues:  # requested and obtained money
        #     return 'MANUAL', "Your account is under review due to reports of fraud.", HIGH_PRI
        # else:  # requested but did not obtain money
        if money_message(completed_report.get_reported_message()) == "yes":
            return 'BAN', "Your account has been banned due to reports of monetary fraud.", HIGH_PRI
        else:
            return 'MANUAL', "Your account is under review due to reports of fraud", HIGHEST_PRI
    elif Report.IMPERSONATION in reported_issues:
        if impersonating(completed_report.get_reported_message()) == "yes":
            return 'BAN', "Your account has been banned due to reports of impersonation.", HIGH_PRI
        else:
            return 'MANUAL', "Your account is under review due to reports of fraud.", MED_PRI

    elif Report.FALSE_INFO in reported_issues:
        return 'MANUAL', "Your account is under review due to reports of fraud.", MED_PRI
    else:
        return other_report(completed_report)


def other_report(completed_report):
    response = "Your report has been placed in our queue for manual moderation."
    return 'MANUAL', response, LOW_PRI

####################################################################################################

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
    openai.api_key = tokens['openai']

def money_message(message):
        prompt = "Is the person asking for money? \nMessage: " + message + "\nAnswer:"
        response = openai.Completion.create(
            engine="text-davinci-003",
            model='gpt-4',
            prompt=prompt,
            temperature=0.3,
            max_tokens=1,
            n=1,
            stop=None,
        )
        answer = response.choices[0].text.strip()
        return answer.lower() == "yes"

def impersonating(message):
    prompt = "Do you believe this person is impersonating someone else? \nMessage: " + message + "\nAnswer:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.3,
        max_tokens=1,
        n=1,
        stop=None,
    )
    answer = response.choices[0].text.strip()
    return answer.lower() == "yes"

def harrassment(message):
    prompt = "Do you believe this message contains harrassment? \nMessage: " + message + "\nAnswer:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.3,
        max_tokens=1,
        n=1,
        stop=None,
    )
    answer = response.choices[0].text.strip()
    return answer.lower() == "yes"

def spam(message):
    prompt = "Do you believe this message contains spam content? \nMessage: " + message + "\nAnswer:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.3,
        max_tokens=1,
        n=1,
        stop=None,
    )
    answer = response.choices[0].text.strip()
    return answer.lower() == "yes"

def threat(message):
    prompt = "Does this message contain a threat against anyone or does this message imply danger? \nMessage: " + message + "\nAnswer:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.3,
        max_tokens=1,
        n=1,
        stop=None,
    )
    answer = response.choices[0].text.strip()
    return answer.lower() == "yes"

class ModBot(discord.Client):
    REVIEW_REPORT = "review report"
    USER_REPORTS = "generate "

    def __init__(self):
        intents = discord.Intents.default()
        try:
            intents.message_content = True
        except:
            intents.messages = True

        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.flagged_users = {}  # Map of users that have been flagged to users that have flagged them (for moderator review)
        self.reports_by_user = {}  # Map from user to list of reports by the user
        self.reports_about_user = {}  # Map from user to list of reports against them
        self.manual_check_queue = PriorityQueue()  # Queue of reports to be manually reviewed prioritized by severity
        self.in_prog_reviews = {}  # Map of mod-channel message ids to reports for reports currently in review
        self.unique = count()

        self.severity1 = [Report.THREAT, Report.SPAM, Report.HARASSMENT, Report.FALSE_INFO, Report.NOT_INTERESTED,
                        Report.OTHER]
        self.severity2 = [Report.FRAUD, Report.REQUESTED_MONEY, Report.IMPERSONATION]
        self.severity3 = [Report.OBTAINED_MONEY, Report.IMMINENT_DANGER]

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
        # mod_channel = self.mod_channels[message.guild.id]
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_raw_reaction_add(self, payload):
        # Only look for reacts in the DMs 
        if not payload.guild_id:
            await self.handle_dm_react(payload)

        elif payload.channel_id == self.mod_channels[payload.guild_id].id:
            await self.handle_mod_react(payload)

    async def handle_dm_react(self, payload):
        author_id = payload.user_id
        message_id = payload.message_id
        responses = []
        logger.info(payload.emoji)
        logger.info(str(payload.emoji.name))

        # Only respond to reacts if they're part of a reporting flow
        if author_id not in self.reports or message_id not in self.reports[author_id].reporting_message_ids:
            logger.info("message id " + str(message_id) + " not in reports")
            return

        channel = await self.fetch_channel(payload.channel_id)
        responses = await self.reports[author_id].handle_react(payload)
        for r in responses:
            if not r:
                continue
            # If response prompts user for further action, save the message id
            if r.startswith("You reported fraud. Please react"):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.FRAUD_LEVEL
            elif r.startswith("You reported his person has asked you for money. Please react"):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.MONEY_LEVEL
            elif r.startswith("Thank you for reporting."):
                sent = await channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.BLOCK_LEVEL
            else:
                await channel.send(r)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `done` command to complete an in progress report.\n"
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

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            # If response prompts user for further action, save the message id
            if "Please react with one or more of the following to specify a reason for this report" in r:
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.FIRST_LEVEL
            elif r.startswith("Thank you for reporting."):
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.BLOCK_LEVEL
            elif r.startswith("You selected other."):
                sent = await message.channel.send(r)
                self.reports[author_id].reporting_message_ids[sent.id] = BotReactMessage.OTHER_THREAD
            else:
                await message.channel.send(r)

        # If the report is canceled, remove it from our map
        if self.reports[author_id].report_canceled():
            self.reports.pop(author_id)

        # If the report is complete, remove it from our map but flag the reported user
        if self.reports[author_id].report_complete():
            # self.flagged_users[reported_user_id] = (author_id, self.reports[author_id].reported_issues)
            # TODO: do something with this information (maybe more for milesotne 3)
            completed_report = self.reports.pop(author_id)
            user_making_report = author_id
            user_being_reported = completed_report.reported_user_id

            if user_making_report not in self.reports_by_user:
                self.reports_by_user[user_making_report] = []
            self.reports_by_user[user_making_report].append(completed_report)

            if user_being_reported not in self.reports_about_user:
                self.reports_about_user[user_being_reported] = []
            self.reports_about_user[user_being_reported].append(completed_report)

            decision, message, severity = new_report(completed_report, user_being_reported,
                                                          user_making_report, self.reports_by_user,
                                                          self.reports_about_user)
            if decision == "MANUAL":
                # Feel free to change any of these 
                severity = 1
                if any(x in self.severity1 for x in completed_report.reported_issues):
                    severity = 4
                if any(x in self.severity2 for x in completed_report.reported_issues):
                    severity = 3
                if any(x in self.severity3 for x in completed_report.reported_issues):
                    severity = 1
                self.manual_check_queue.put((severity, next(self.unique), completed_report))
            else:
                if decision == "BAN":  # Remove account
                    user_reported = await self.fetch_user(user_being_reported)
                    reporter = await self.fetch_user(user_making_report)
                    await user_reported.send(
                        "We detected fraudulent activity on your account. We will be banning your account. ")
                    await reporter.send("We took action against " + user_reported.name + " who you recently reported. "
                                                                                                "Thank you for keeping our platform safe.")
                    self.in_prog_reviews.pop(msg_id) 

                elif decision == "SUSPEND":  # Suspend for 15 days
                    user_reported = await self.fetch_user(user_being_reported)
                    reporter = await self.fetch_user(user_making_report)
                    await user_reported.send("We detected fraudulent activity on your account. "
                                            "We will be suspending your account for 15 days.")
                    await reporter.send("We took action against " + user_reported.name + " who you recently reported. "
                                                                                                "Thank you for keeping our platform safe.")
                    self.in_prog_reviews.pop(msg_id) 

                elif "NO_ACTION":  # No action
                    user_reported = await self.fetch_user(user_being_reported)
                    reporter = await self.fetch_user(user_making_report)
                    await reporter.send(
                        "We did not detect any fraudulent information in the message/profile submitted. "
                        "The next course of action to protect yourself can include: " + "\n"
                                                                                    + "\t" + "Blocking " + user_reported.name + "\n"
                                                                                                                            + "\t" + "Calling 911 if this is an emergency.")
        # for r in responses:
        #   await message.channel.send(r)

    async def handle_channel_message(self, message):
        if message.channel.name == f'group-{self.group_num}':
            # Forward the messages from group channel to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            
            url, money = self.eval_text(message.content)
            # TO-DO figure out how we want to use different and make report
            if url:
                await message.channel.send("Beware of the links posted in this chat! We cannot guarantee their safety and do not recommend clicking external links.")
            if money:
                 await message.channel.send("We have detected a request for money in the previous messages. Beware of fraud, and please report this message if you suspect this person of fraud.")
            #await mod_channel.send(self.code_format(scores))

        if message.channel.id == self.mod_channels[message.guild.id].id:
            # if a mod is chatting in the mod group:
            await self.handle_mod_msg(message)



    async def handle_mod_msg(self, message):
        mod_channel = self.mod_channels[message.guild.id]
        if message.content == self.REVIEW_REPORT:
            # If a moderator is asking to review the next report
            if self.manual_check_queue.empty():
                await mod_channel.send("Nothing to review")
            else:
                # TODO: Handle report.reported_msg is encoded in some way - milestone 3


                pri, _, report = self.manual_check_queue.get()
                msg = "Report:" + "\n"
                msg += "\t" + "Report against user: " + str(report.reported_user_id) + "\n"
                msg += "\t" + "Report by user: " + str(report.reporting_user_id) + "\n"
                msg += "\t" + "Reported issues: " + "\n"
                for i in report.reported_issues:
                    msg += "\t" + "\t" + str(i) + "\n"
                msg += "\t" + "Reported message: " + str(report.reported_msg) + "\n"
                msg += "React with 1 to ban, 2 to suspend, 3 to warn, 4 for no action."
                sent = await mod_channel.send(msg)
                self.in_prog_reviews[sent.id] = report




        # #TODO: (maybe) for milestone 2: I haven't tested this but the idea here is to generate a report
        # # of everything a user has reported in case they ask (for police purposes etc)
        # elif message.content.startswith(self.USER_REPORTS):
        #     #TODO: I have tested this zero
        #     l = message.content.split(' ')
        #     user_id = int(l[1])
        #     #TODO: format the reports_by_user, this will print python garbage
        #     await self.mod_channel.send(str(self.reports_by_user[user_id]))

    async def handle_mod_react(self, payload):
        # once a mod reacts to a manual review message, this should send the suspended/banned user a message simulating the bad
        msg_id = payload.message_id
        if msg_id not in self.in_prog_reviews:
            return

        report = self.in_prog_reviews[msg_id]
        reported_user = report.reported_user_id
        reporting_user = report.reporting_user_id
        emoji = payload.emoji

        if str(emoji.name) == '1️⃣':  # Remove account
            user_reported = await self.fetch_user(reported_user)
            user_making_report = await self.fetch_user(reporting_user)
            await user_reported.send(
                "We detected fraudulent activity on your account. We will be banning your account. ")
            await user_making_report.send("We took action against " + user_reported.name + " who you recently reported. "
                                                                                          "Thank you for keeping our platform safe.")
            self.in_prog_reviews.pop(msg_id)

        elif str(emoji.name) == '2️⃣':  # Suspend for 15 days
            user_reported = await self.fetch_user(reported_user)
            user_making_report = await self.fetch_user(reporting_user)
            await user_reported.send("We detected fraudulent activity on your account. "
                                     "We will be suspending your account for 15 days.")
            await user_making_report.send("We took action against " + user_reported.name + " who you recently reported. "
                                                                                          "Thank you for keeping our platform safe.")
            self.in_prog_reviews.pop(msg_id)

        elif str(emoji.name) == '3️⃣':  # Warning
            user_reported = await self.fetch_user(reported_user)
            user_making_report = await self.fetch_user(reporting_user)
            await user_reported.send("We detected fraudulent activity on your account. "
                                     "This is a warning; continuation of fraudulent activity will result in escalated action.")
            await user_making_report.send("We took action against " + user_reported.name + " who you recently reported. "
                                                                                          "Thank you for keeping our platform safe.")
            self.in_prog_reviews.pop(msg_id)

        elif str(emoji.name) == '4️⃣':  # No action
            user_reported = await self.fetch_user(reported_user)
            user_making_report = await self.fetch_user(reporting_user)
            await user_making_report.send(
                "We did not detect any fraudulent information in the message/profile submitted. "
                "The next course of action to protect yourself can include: " + "\n"
                                                                                "\t" + "Blocking " + user_reported.name + "\n"
                                                                                                                         "\t" + "Calling 911 if this is an emergency.")
            self.in_prog_reviews.pop(msg_id)

    # Adds auto check if URL is in included--should automatically flag, it's a design decision to just say
    # no URLS at all
    def check_for_url(self, message):
        url1 = re.search("^[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$", message)
        url2 = re.search("^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$", message)
        if url1 or url2:
            return True
        return False
    
    """
    def money_related_message(self, message):
        money_keywords = ['money', 'cash', 'financial support', 'donation', 'fund', 'fundraising', 'sponsorship']

        message = message.lower()  # Convert message to lowercase for case-insensitive matching

        for keyword in money_keywords:
            if keyword in message:
                return True
        return False
    """

    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        url = self.check_for_url(message)
        money = money_message(message)
        # impersonate = self.impersonating(message) MIGHT BE HARDER TO DO WITH A SINGLE MESSAGE
        return url, money

    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text + "'"


client = ModBot()
client.run(discord_token)


