# bot.py
import discord
from discord.ext import commands
from unidecode import unidecode
import csam_text_classification as ctc
import csam_image_classifier as cic
import os
import json
import logging
import re
import requests
from report import Report, ModReport
import pdb

# REFERENCE: https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
import re
regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)


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
    openai_org = tokens['openai_org']
    openai_key = tokens['openai_key']

def csam_detector(message):
    result = ctc.content_check(unidecode(message), openai_org, openai_key)
    if 'illegal' in result.lower():
        return result
    else:
        return ''

def csam_link_detector(modBot, message):
    # print(urls)
    return any([url in message or any([alias in message for alias in modBot.blacklisted_urls[url]]) for url in modBot.blacklisted_urls])


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.unresolved_reports = {}

        self.resolving_report = False
        self.currentReports = []
        self.adding_link_stage = 0
        # map URLs to Reports
        self.blacklisted_urls_path = 'blacklisted_sites.json'

        self.blacklisted_urls = {}
        if not os.path.isfile(self.blacklisted_urls_path):
            raise Exception(f"{self.blacklisted_urls_path} not found!")
        with open(self.blacklisted_urls_path) as f:
            self.blacklisted_urls = json.load(f)
            # self.blacklisted_urls = urls['urls']

        self.added_link = None

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
                    self.mod_channel = channel
        

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
            print(message)
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

        # If the report is complete or cancelled, remove it from our map
        # If the report is cancelled 
        if self.reports[author_id].report_cancelled():
            self.reports.pop(author_id)
        if self.reports[author_id].report_complete():
            abuse_report = self.reports[author_id].return_abuse_report()
            # send each string in the abuse report to the mod channel
            mod_channel = self.mod_channel
            abuse_report.append("\n\n")
            abuse_report_mod_channel_message = await mod_channel.send(''.join(abuse_report))
            self.unresolved_reports[abuse_report_mod_channel_message.jump_url] = self.reports[author_id]
            # for abuse_report_string in abuse_report:
            #     await mod_channel.send(abuse_report_string)
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        # if not message.channel.name == f'group-{self.group_num}':
        #     return
        responses = []
        # Forward the message to the mod channel if and only if it's not in the mod channel already.
        # if message.channel.name == f'group-{self.group_num}':
            # mod_channel = self.mod_channels[message.guild.id]
            # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        banned_user = message.author.name
        # For now we are going to use this as a placeholder until Milestone 3. 
        # check if the message contains images
        # CHECKS FOR NON MOD CHANNELS:
        if message.channel.id != self.mod_channels[message.guild.id].id:
            if (message.attachments):
                for attachment in message.attachments:
                    if (cic.image_classifier(attachment.url)):
                        mod_channel = self.mod_channels[message.guild.id]
                        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{attachment.url}"')
                        await mod_channel.send(f"Our CSAM detection tool has flagged {banned_user} due to detected CSAM. Is the above message CSAM?")
                        # remove the message from the channel and reply to the message privately saying "this message was flagged as abusive material and removed."
                        await message.delete()
                        try:
                            await message.author.send("This message was flagged as abusive material and removed.")
                        except:
                            await message.channel.send("This message was flagged as abusive material and removed.")

                        return
            csam_evaluation = csam_detector(message.content)
            if (len(csam_evaluation) != 0): 
                # await message.delete()
                mod_channel = self.mod_channels[message.guild.id]
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                await mod_channel.send(f'Our systems have evaluated this message as inappropriate, with justification {csam_evaluation}.')
                await message.delete()
                await message.author.send(f'Our CSAM detection tool has flagged your message: \n > {message.content} \n due to containing kitten references. The message has been deleted.')
                return
            
            # link blocking
            if (csam_link_detector(self, message.content)):
                mod_channel = self.mod_channels[message.guild.id]
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                await mod_channel.send(f"Our CSAM detection tool has flagged {banned_user} due to linking to known sources of CSAM. The message has been deleted.")
                await message.delete()
                await message.author.send(f'Our CSAM detection tool has flagged your message: \n > {message.content} \n due to linking to known sources of CSAM. The message has been deleted.')
                return
        

        # if (message.content.lower() == "report"):
            # If we don't currently have an active report for this user, add one
        # if banned_user not in self.reports:
        #     self.reports[banned_user] = ModReport(self)
        # elif self.reports[banned_user].report_complete():
        #     self.reports.pop(banned_user)
        #     self.reports[banned_user] = ModReport(self)

            # #User Report Flow
            # responses = await self.reports[banned_user].handle_message(message)
            # for r in responses:
            #     await message.channel.send(r)

            #Moderator Report Handling
        # only start mod reports when messages are sent in the mod channel
        # Reports should be in format  
        if message.channel.id == self.mod_channels[message.guild.id].id:
            # # if "report" == message.content:

            # Handle a help message
            if message.content == Report.HELP_KEYWORD:
                reply =  "Use the `report` command in reply to a valid (and unresolved) user report to begin the process of resolving a report.\n"
                reply += "Use the `cancel` command to cancel the report resolution or link adding process.\n"
                reply += "Use the `show` command to show all unresolved user reports\n"
                reply += "Use the `add link` command to add a link to the blocklist\n"
                reply += "Use the `view blocked links` to view all blocked links.\n"

                await message.channel.send(reply)
                return
            
            if "show" == message.content:
                # print(self.unresolved_reports)
                reply = ["Current Unresolved Reports:\n"]
                reply.extend([f"{self.unresolved_reports[url].report_type}: {url}\n" for url in self.unresolved_reports.keys()])
                if len(self.unresolved_reports) == 0:
                    reply += ["No Unresolved Reports!"]
                await self.mod_channels[message.guild.id].send(''.join(reply))
                return
            # print(message.reference)
            if "report" == message.content:
                if not message.reference or not message.reference.jump_url or message.reference.jump_url not in self.unresolved_reports:
                    await self.mod_channels[message.guild.id].send("Please reply a valid report message to begin resolving it.")
                    return
                modReport = ModReport(self)
                userReport = self.unresolved_reports[message.reference.jump_url]
                original_user_report_message = await self.message_from_link(message.reference.jump_url)
                self.currentReports = [original_user_report_message, modReport, userReport]
                responses = await modReport.handle_mod_message(userReport.message)
                # await self.mod_channels[message.guild.id].send(responses.join())
                for r in responses:
                    await self.mod_channels[message.guild.id].send(r)
                    # scores = self.eval_text(userReport.message.content)
                    self.resolving_report = True
                return
                    # await self.mod_channels[message.guild.id].send(self.code_format(scores))
            if "cancel" == message.content:
                if self.adding_link_stage > 0:
                    # if self.adding_link_stage == 1:
                    if self.adding_link_stage ==2:
                        self.blacklisted_urls.pop(self.added)
                    self.adding_link_stage = 0
                    await self.mod_channels[message.guild.id].send(f"Process to block link cancelled.")
                    return
                self.resolving_report = False
                if self.currentReports:
                    reportMsg, modReport, userReport = self.currentReports
                    await self.mod_channels[message.guild.id].send(f"Canceled resolving report: {reportMsg.jump_url}")
                self.currentReports = []
                return
            
            if "add link" == message.content and self.adding_link_stage == 0:
                self.adding_link_stage = 1
                await self.mod_channels[message.guild.id].send(f"Enter URL to block.")
                return 
            if self.adding_link_stage == 1:
                if re.match(regex, message.content):
                    self.blacklisted_urls[message.content] = []
                    self.adding_link_stage = 2
                    self.added_link = message.content
                    await self.mod_channels[message.guild.id].send(f"Enter aliases for this URL, separated by commas with no spaces.")
                    return
                else:
                    await self.mod_channels[message.guild.id].send(f"Invalid input. Enter a valid URL or `cancel` to stop the process.")
                    return
            if self.adding_link_stage == 2:
                self.blacklisted_urls[self.added_link] = message.content.split(',')
                await self.mod_channels[message.guild.id].send(f"URL and aliases added to the blacklist. \n URL: {self.added_link} \nAliases: {message.content.split(',')}")
                json_object = json.dumps(self.blacklisted_urls, indent=4)
                with open(self.blacklisted_urls_path, "w") as outfile:
                    outfile.write(json_object)
                self.adding_link_stage = 0
                self.added_link = None
                return

            if "view blocked links" == message.content:
                formatted = [f"URL: {url} \nAliases: {self.blacklisted_urls[url]}" for url in self.blacklisted_urls]
                separator = '\n\n'
                await self.mod_channels[message.guild.id].send(f"*Blocked links*:\n\n {separator.join(formatted)}")
                return
            
            if self.resolving_report and self.currentReports:
                reportMsg, modReport, userReport = self.currentReports
                if not modReport.report_complete() and message == "cancel":
                    self.resolving_report = False
                    self.currentReports = []
                    await self.mod_channels[message.guild.id].send(f"Canceled resolving report: {reportMsg.jump_url}")
                    return
                responses = await modReport.handle_mod_message(message)
                for r in responses:
                    await self.mod_channels[message.guild.id].send(r)
                if modReport.report_complete():
                    await reportMsg.edit(content = reportMsg.content + "\n\n REPORT RESOLVED")
                    self.unresolved_reports.pop(reportMsg.jump_url)
                    self.resolving_report = False
                    self.currentReports = []


    async def on_message_edit(self, before, after):
        if before.content != after.content:
            # if csam_detector(after.content):
            #     await after.delete()
            #     await self.mod_channels[after.guild.id].send(f"We have banned user {after.author.name}, reported to NCMEC and removed the content.")
            #     return
            if (csam_link_detector(self, after.content)):
                # await message.delete()
                mod_channel = self.mod_channels[after.guild.id]
                await mod_channel.send(f'Forwarded message:\n{after.author.name}: "{after.content}"')
                await mod_channel.send(f"Our CSAM detection tool has flagged {after.author} due to linking to known sources of CSAM. The message has been deleted.")
                await after.delete()
                await after.author.send(f'Our CSAM detection tool has flagged your message: > {after.content} \n due to linking to known sources of CSAM. The message has been deleted.')
        
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"
    
    async def message_from_link(self, message):
            m = re.search('/(\d+)/(\d+)/(\d+)', message)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            return message


bot = ModBot()
bot.run(discord_token)