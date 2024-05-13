from constants import UserResponse, SpecificIssue, USER_REPORT_KEY
from enum import Enum, auto
import discord
import re

class State(Enum):
    MOD_START = auto()
    AWAITING_CONFIRMATION = auto()
    IS_DANGEROUS = auto()
    IS_ADVERSARIAL = auto()
    REVIEW_COMPLETE = auto()
    CHECK_POLITICAL = auto()
    REMOVE_POST = auto()
    FURTHER_ACTION_REPORTER = auto()
    FURTHER_ACTION_POSTER = auto()
    HISTORY = auto()

class ModReview:    
    def __init__(self, message, report_info, reported_message, report_history, author_dm_channel, group_channel):
        self.state = State.MOD_START
        self.message = message
        self.report_info = report_info
        self.reported_message = reported_message
        self.report_history = report_history
        self.author_dm_channel = author_dm_channel
        self.group_channel = group_channel

    async def handle_message(self, message):
        '''
        This function makes up the meat of the mod-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. 
        '''
        
        if self.state == State.MOD_START:
            reported_abuse = self.report_info[UserResponse.ABUSE_TYPE]
            reported_abuse_desc = USER_REPORT_KEY[reported_abuse]["name"].lower()
            reported_specifics = self.report_info[UserResponse.SPEC_ISSUE]
            reported_specifics_desc = USER_REPORT_KEY[reported_abuse][reported_specifics].lower()

            reply =  "A new report has been completed. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Below is the reported message: \n"
            reply += f'{self.reported_message.author.name}: "{self.reported_message.content}"\n\n'
            
            if reported_abuse != SpecificIssue.OTHER:
                reply += f'The post was categorized as {reported_abuse_desc}. Speficially, it is categorized as {reported_specifics_desc}. Is this accurate? (y/n) \n'

                self.state = State.AWAITING_CONFIRMATION
                return [reply]
            else:
                self.state = State.REVIEW_COMPLETE
                comments = self.report_info[UserResponse.SOURCE]
                author = self.reported_message.author.name
                return [f'{author} had the following comments about {reported_specifics_desc}: \n\n "{comments}" \n\n The review has been closed.']
        
        elif self.state == State.AWAITING_CONFIRMATION:
            if message.content == 'y':
                if self.report_info[UserResponse.ABUSE_TYPE] == SpecificIssue.DISINFORMATION and self.report_info[UserResponse.SPEC_ISSUE] == SpecificIssue.OTHER:
                    self.is_political = True
                    self.state = State.CHECK_POLITICAL
                    return self.check_political()
                else:
                    self.state = State.IS_DANGEROUS
                    return self.check_danger()
            elif message.content == 'n':
                self.state = State.IS_ADVERSARIAL
                return self.check_adversarial() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 
        
        elif self.state == State.CHECK_POLITICAL:
            # after checking if the source backs up claims of political disinformation
            # we go back to see if it's dangerous / adversarial
            if message.content == 'y':
                self.state = State.IS_DANGEROUS
                return self.check_danger()
            elif message.content == 'n':
                self.state = State.IS_ADVERSARIAL
                return self.check_adversarial() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 

        elif self.state == State.IS_DANGEROUS:
            if message.content == 'y':
                self.state = State.REVIEW_COMPLETE
                return self.process_danger()
            elif message.content == 'n':
                self.state = State.REMOVE_POST
                reply = await self.remove_post() 
                return reply
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 

        elif self.state == State.IS_ADVERSARIAL: 
            if message.content == 'y':
                self.state = State.FURTHER_ACTION_REPORTER
                return self.process_adversarial()
            elif message.content == 'n':
                self.state = State.REVIEW_COMPLETE
                return self.no_action() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 

        elif self.state == State.REMOVE_POST:
            if message.content == 'y':
                self.state = State.HISTORY
                return self.process_history()
            elif message.content == 'n':
                self.state = State.FURTHER_ACTION_POSTER
                return self.finish_review() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 

        elif self.state == State.FURTHER_ACTION_POSTER:
            if message.content == 'y':
                self.state = State.REVIEW_COMPLETE
                reply = await self.ban_user()
                return reply
            elif message.content == 'n':
                self.state = State.REVIEW_COMPLETE
                return self.finish_review() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 
            
        elif self.state == State.HISTORY:
            if message.content == 'y':
                self.state = State.REVIEW_COMPLETE
                reply = await self.ban_user()
                return reply
            elif message.content == 'n':
                self.state = State.REVIEW_COMPLETE
                return self.finish_review() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 

        elif self.state == State.FURTHER_ACTION_REPORTER:
            if message.content == 'y':
                self.state = State.REVIEW_COMPLETE
                reply = await self.ban_reporter()
                return reply
            elif message.content == 'n':
                self.state = State.REVIEW_COMPLETE
                return self.finish_review() 
            else:
                return ["Invalid response. Please type one of 'y' for Yes, or 'n' for No"] 
            
        return []


    def check_political(self):
        # check if the political information is backed up by the source
        sources = self.report_info[UserResponse.SOURCE]
        reply = ""

        if sources == "":
            reply += "Please do some research to verify whether or not this ad contains political disinformation.\n"
            reply += "Do your finding support that this ad contains political disinformation? (y/n)"
        else:
            reply += "The user indicated the following source/reasoning as to why this ad contains political disinformation: \n\n"
            reply += sources
            reply += "\n\nCan you verify if this ad contains political disinformation? (y/n)"

        return [reply]

    def check_danger(self):
        # check if there's any signs of potential illegal crime or imminent danger
        return ["Does the message indicate any signs of potential illegal crime or imminent danger? (y/n)"]

    def check_adversarial(self):
        # check if there's any sign of potential adversarial reporting
        return ["No action will be taken regarding this post. \nHowever, we would like to check if this report indicates any signs of adversarial reporting. Does this report demonstrate signs of coordinated harrasment via reporting? (y/n)"]

    def process_danger(self):
        if self.reported_message.author.name not in self.report_history:
            self.report_history[self.reported_message.author.name] = 1

        return ["We have contacted local authorities and sent them the reported post. Thank you for completing the moderator review of this post."]
    
    def no_action(self):
        # just return a message saying that no action needs to be taken
        return ["No action will be taken regarding this post. Thank you for completing the moderator review of this post."]
    
    async def remove_post(self):
        # send a message saying we've removed the post. then, ask to see if we want to
        # see if the user has a history of violations
        await self.group_channel.send(f'(Simulated deletion) The following message has been removed: \n{self.reported_message.author.name}: "{self.reported_message.content}"') 

        reply = "We have deleted the message in the channel. Would you like to investigate the poster's history of violation? (y/n)"

        return [reply]

    def further_action(self):
        # should we take further action
        reply = f"Thank you. Would you like to ban {self.reported_message.author.name}?"

        return [reply]

    def process_history(self):
        # look into user's history
        if self.reported_message.author.name not in self.report_history:
            self.report_history[self.reported_message.author.name] = 0

        past_reports = self.report_history.get(self.reported_message.author.name)

        reply = f"{self.reported_message.author.name} has {past_reports} past violations on this server. Would you like to ban {self.reported_message.author.name}? (y/n)"

        self.report_history[self.reported_message.author.name] += 1

        return [reply]

    async def ban_user(self):
        # send a message indicating poster was banned
        reported_abuse = self.report_info[UserResponse.ABUSE_TYPE]
        reported_abuse_desc = USER_REPORT_KEY[reported_abuse]["name"].lower()
        reported_specifics = self.report_info[UserResponse.SPEC_ISSUE]
        reported_specifics_desc = USER_REPORT_KEY[reported_abuse][reported_specifics].lower()
        
        ban_message = f'(Simulated ban) {self.reported_message.author.name} has been banned from sending messages in the server, due to violating this policy: {reported_abuse_desc} -> {reported_specifics_desc}.'
        await self.group_channel.send(ban_message)

        return [f'We have banned {self.reported_message.author.name}. Thank you for completing the moderator review of this post.']

    def process_adversarial(self):
        return ["Would you like to ban the reporter of the message? (y/n)"]

    async def ban_reporter(self):
        # send a DM indicating reporter was banned
        await self.author_dm_channel.send("(Simulated ban) You have been banned from reporting messages in the server, due to coordinated harrassment via reporting.")

        reporter = self.report_info["reporter"]
        return [f"We have banned {reporter}. Thank you for completing the moderator review of this post."] 

    def finish_review(self):
        return ["Thank you for completing the moderator review of this post."]

    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE


    