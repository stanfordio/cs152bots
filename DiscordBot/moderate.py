# moderate.py
import discord
from enum import Enum, auto
import re

class State(Enum):
    MODERATE_INIT = auto()
    MODERATE_BEGIN = auto()
    MODERATE_COMPLETE = auto()
    CONFIRM_GOVERNMENT = auto()
    IMMINENT_DANGER = auto()
    SEPARATE_POLICY_VIOLATION = auto()
    SEND_TO_LAW_ENFORCEMENT = auto()
    DISMISINFO_CATEGORY = auto()
    SELECT_MODERATION_TEAM = auto()
    NUM_VIOLATIONS = auto()
    END = auto()

class Moderator:
    START_KEYWORD = "moderate"
    def __init__(self, client):
        # self.bot = bot
        self.client = client
        self.state = None

    async def handle_moderation(self, message, reports_queue):
        # Check if the message is the "moderate" command
        if message.content == "moderate":
            self.state = State.MODERATE_INIT
            if len(reports_queue) == 0:
                return ["There are no reports in the queue! Check back later."]
            else:
                reply = "There are " + str(len(reports_queue)) + " reports in the queue.\n"
                reply += "Would you like to begin?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                self.state = State.MODERATE_BEGIN
                return [reply]
            
        if self.state == State.MODERATE_BEGIN:
            if message.content == "1":
                self.state = State.CONFIRM_GOVERNMENT
                reply = "Beginning moderation process...\n"
                reply = "The top report in the queue is from the user:   " + reports_queue[0]['author'] + "\n"
                reply += "Confirm that this post was created by a government official, agency, or state-controlled media.\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            elif message.content == "2":
                self.state = State.END
                return ["Moderation cancelled."]
        
        if self.state == State.CONFIRM_GOVERNMENT:
            reply = "Here is the content of the report:\n"
            reply += "message: " + reports_queue[0]['message'] + "\n"
            reply += "reason for report: " + reports_queue[0]['reason'] + "\n"
            if message.content == "1":
                self.state = State.IMMINENT_DANGER
                reply += "Does this post represent imminent violence?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            elif message.content == "2":
                self.state = State.SEPARATE_POLICY_VIOLATION
                reply += "Does this post violate other platform policies?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            
        if self.state == State.SEPARATE_POLICY_VIOLATION:
            if message.content == "1":
                self.state = State.SELECT_MODERATION_TEAM
                reply = "Please select a moderation team to review this post.\n"
                return [reply]
            elif message.content == "2":
                self.state = State.MODERATE_COMPLETE
                reply = "No further action is needed.\n"
                reports_queue.pop(0)
                reply += self.complete_report(reports_queue)
                return [reply]
            
        if self.state == State.SELECT_MODERATION_TEAM:
            self.state = State.MODERATE_COMPLETE
            reply = "Moderation team selected. No further actions is needed\n"
            reports_queue.pop(0)
            reply += self.complete_report(reports_queue)
            return [reply]

        if self.state == State.IMMINENT_DANGER:
            if message.content == "1":
                self.state = State.MODERATE_COMPLETE
                reply = "Please send details to law enforcement.\n"
                reply += await self.delete_message_with_url(reports_queue[0]['link'], reports_queue[0]['author'], "imminent danger threat")
                reply += "The user account has been suspended until review by a committee\n"
                reports_queue.pop(0)
                reply += self.complete_report(reports_queue)
                return [reply]
            elif message.content == "2":
                if reports_queue[0]['reason'] == "Misleading/false information from government group":
                    self.state = State.DISMISINFO_CATEGORY
                    reply = "This post was reported in the category: "+ reports_queue[0]['content_type'] + "\n"
                    reply += "Please categorize this post as one of the following:\n"
                    reply += "1. Dis/Misleading\n"
                    reply += "2. Inciting Harassment\n"
                    reply += "3. Hate Speech\n"
                    reply += "4. Does not apply to any of the above\n"
                    reply += "Please respond with '1', '2', '3', or '4'."
                    return [reply]
                else:
                    self.state = State.SEPARATE_POLICY_VIOLATION
                    reply = "Does this post violate other platform policies?\n"
                    reply += "1. Yes\n"
                    reply += "2. No\n"
                    reply += "Please respond with '1' or '2'."
                    return [reply]
        
        if self.state == State.DISMISINFO_CATEGORY:
            if message.content == "1":
                self.state = State.NUM_VIOLATIONS
                reply = await self.comment_under_message_with_url(reports_queue[0]['link'], "This is a comment containing dis/misleading information.")
                reply += "Do this user have 3 or more violations in the past month?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            elif message.content == "2":
                self.state = State.NUM_VIOLATIONS
                reply = "This post has been categorized as inciting harassment.\n"
                reply += await self.delete_message_with_url(reports_queue[0]['link'], reports_queue[0]['author'], "inciting harassment")
                reply += "Do this user have 3 or more violations in the past month?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            elif message.content == "3":
                self.state = State.NUM_VIOLATIONS
                reply = "This post has been categorized as hate speech.\n"
                reply += await self.delete_message_with_url(reports_queue[0]['link'], reports_queue[0]['author'], "hate speech against")
                reply += "Do this user have 3 or more violations in the past month?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            elif message.content == "4":
                self.state = State.SEPARATE_POLICY_VIOLATION
                reply = "Does this post violate other platform policies?\n"
                reply += "1. Yes\n"
                reply += "2. No\n"
                reply += "Please respond with '1' or '2'."
                return [reply]
            
        if self.state == State.NUM_VIOLATIONS:
            if message.content == "1":
                self.state = State.MODERATE_COMPLETE
                reply = "This user has 3 or more violations in the past month.\n"
                reply += "The user's account has been suspended until review by committee.\n"
                reply += "The reason for account suspension has been publicly posted for transparency.\n"
                reports_queue.pop(0)
                reply += self.complete_report(reports_queue)
                return [reply]
            elif message.content == "2":
                self.state = State.MODERATE_COMPLETE
                reply = "No further action is needed\n"
                reports_queue.pop(0)
                reply += self.complete_report(reports_queue)
                return [reply]

        return []
    
    def complete_report(self, reports_queue):
        if len(reports_queue) > 0:
            self.state = State.MODERATE_BEGIN
            reply = "\nThere are " + str(len(reports_queue)) + " reports in the queue.\n"
            reply += "Would you like to continue?\n"
            reply += "1. Yes\n"
            reply += "2. No\n"
            reply += "Please respond with '1' or '2'."
            return reply
        else:
            self.state = State.END
            return "Moderation process complete! There are no more reports in the queue."
    
    async def delete_message_with_url(self, url, author, reason):
        # Parse out the three ID strings from the message link
        m = re.search('/(\d+)/(\d+)/(\d+)', url)
        if not m:
            return "I'm sorry, I couldn't read that link. Please try again."

        guild = self.client.get_guild(int(m.group(1)))
        if not guild:
            return "I cannot delete messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."

        channel = guild.get_channel(int(m.group(2)))
        if not channel:
            return "It seems this channel was deleted or never existed. Please try again."

        try:
            message = await channel.fetch_message(int(m.group(3)))
        except discord.errors.NotFound:
            return "It seems this message was deleted or never existed. Please try again."

        # Delete the message
        await message.delete()
        await channel.send(f"A message from {author} was deleted for the following reason: {reason}")
        return "The post has been deleted and the reason for removal has been provided to the public.\n"
    
    async def comment_under_message_with_url(self, url, comment):
        # Parse out the three ID strings from the message link
        m = re.search('/(\d+)/(\d+)/(\d+)', url)
        if not m:
            return "I'm sorry, I couldn't read that link. Please try again."

        guild = self.client.get_guild(int(m.group(1)))
        if not guild:
            return "I cannot comment in guilds that I'm not in. Please have the guild owner add me to the guild and try again."

        channel = guild.get_channel(int(m.group(2)))
        if not channel:
            return "It seems this channel was deleted or never existed. Please try again."

        try:
            message = await channel.fetch_message(int(m.group(3)))
        except discord.errors.NotFound:
            return "It seems this message was deleted or never existed. Please try again."

        # Send a comment as a reply to the message
        await message.reply(comment)

        return "This post has been categorized as dis/misleading and has been flagged for all users.\n"
