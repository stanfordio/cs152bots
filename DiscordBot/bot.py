# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, AbuseType, MisinfoCategory, HealthCategory, NewsCategory, State
from user_stats import UserStats
from classifier.misinfo_classifier import predict_misinformation, load_model
import pdb
import openai

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
    openai_api_key = tokens['openai']

openai.api_key = openai_api_key
client = openai.OpenAI(api_key=openai_api_key)


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.pending_appeals = {} 
        self.active_mod_flow = None # State for the current moderation flow
        self.user_stats = UserStats() # Initialize user statistics tracking
        self.awaiting_appeal_confirmation = {}
        self.awaiting_appeal_reason = {}
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.model = load_model()


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
        if message.author.id in self.pending_appeals:
            # Retrieve all pending appeals for the user
            user_appeals = self.pending_appeals[message.author.id]
            if not user_appeals:
                return

            # Check if the user is in the middle of an appeal confirmation
            if self.awaiting_appeal_confirmation.get(message.author.id):
                if message.content.strip() == '1':  # User wants to appeal
                    await message.channel.send("Please provide your reasoning for appealing:")
                    self.awaiting_appeal_confirmation[message.author.id] = False
                    self.awaiting_appeal_reason[message.author.id] = True
                    return
                elif message.content.strip() == '2':  # User does not want to appeal
                    await message.channel.send("Thank you.")
                    self.awaiting_appeal_confirmation[message.author.id] = False
                    # Reset the appeal state for the user
                    del self.pending_appeals[message.author.id]
                    return
                else:
                    await message.channel.send("Invalid response. Please reply with 1 for Yes or 2 for No.")
                    return

            # Check if the user is providing their appeal reasoning
            if self.awaiting_appeal_reason.get(message.author.id):
                # Process the appeal reasoning
                info = user_appeals[0]

                mod_chan = self.mod_channels[info['guild_id']]

                # Build the appeal notice
                text = (
                    f"APPEAL RECEIVED:\n"
                    f"User: {info['reported_name']}\n"
                    f"Outcome: {info['outcome']}\n\n"
                    f"Original Message:\n{info['original_message']}"
                )
                if info.get('explanation'):
                    text += f"\n\nReason: {info['explanation']}"
                text += f"\n\nAppeal Reason:\n{message.content}"

                # Send to mod channel
                await mod_chan.send(text)

                # Prompt mods for ACCEPT/UPHOLD
                self.active_mod_flow = {
                    'step': 'appeal_review',
                    'info': info,
                    'message_author': info['reported_name'],
                    'context': {},
                    'guild_id': info['guild_id']
                }
                await mod_chan.send("Moderators, please respond with:\n1. ACCEPT\n2. UPHOLD")

                # Acknowledge to user
                await message.channel.send("Your appeal has been submitted and is under review.")
                self.awaiting_appeal_reason[message.author.id] = False
                return

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

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#-mod" channel
        if message.channel.name == f'group-{self.group_num}-mod':
            await self.handle_mod_channel_message(message)
        elif message.channel.name == f'group-{self.group_num}':
            pass
            # prediction = predict_misinformation(message.content, self.model)
            # print(prediction)

    async def start_moderation_flow(
            self,
            report_type,
            report_content,
            message_author,
            user_context=None,
            message_link=None
        ):
            # Determine the initial step based on report type
            if report_type.startswith('ADVERTISING MISINFO'):
                initial_step = 'advertising_done'
            elif (
                report_type.startswith('MISINFORMATION')
                or report_type.startswith('HEALTH MISINFO')
                or report_type.startswith('NEWS MISINFO')
            ):
                initial_step = 'danger_level'
            else:
                initial_step = 'default_done'

            # Store everything (including user_context) up front
            self.active_mod_flow = {
                'step': initial_step,
                'report_type': report_type,
                'report_content': report_content,
                'message_author': message_author,
                'message_link': message_link,
                'user_context': user_context,
                'context': {}
            }

            # Pick any one moderator channel
            mod_channel = None
            for channel in self.mod_channels.values():
                mod_channel = channel
                break

            if not mod_channel:
                return

            # If this is a misinformation‐type report, run the danger‐level flow
            if initial_step == 'danger_level':
                # Update the step
                self.active_mod_flow['step'] = 'confirm_danger_level'

                # Let LLM guess LOW/MEDIUM/HIGH, passing along user_context
                predicted = await self.classify_danger_level(
                    report_content,
                    user_context
                )
                self.active_mod_flow['context']['predicted_danger'] = predicted

                # Build "new report" message and include user_context if provided
                base_msg = (
                    f"A new report has been submitted:\n"
                    f"Type: {report_type}\n"
                    f"Content: {report_content}\n"
                    f"Reported user: {message_author}\n"
                )
                if user_context:
                    base_msg += f"User context: {user_context}\n"

                base_msg += (
                    f"\nSystem suggests danger level: {predicted.upper()}. Do you agree?\n"
                    "1. Yes\n"
                    "2. No"
                )
                await mod_channel.send(base_msg)
                return

            # Otherwise, handle the other two cases
            if initial_step == 'advertising_done':
                await mod_channel.send(
                    "Report sent to advertising team. No further action required."
                )
                self.active_mod_flow = None
                return

            if initial_step == 'default_done':
                # Just show the report, do not prompt for reply
                await mod_channel.send(
                    f"A new report has been submitted:\n"
                    f"Type: {report_type}\n"
                    f"Content: {report_content}\n"
                    f"Reported user: {message_author}"
                )
                self.active_mod_flow = None
                return
            await self.prompt_next_moderation_step(mod_channel)

    async def notify_reported_user(self, user_name, guild, outcome, explanation=None, original_message=None):
        """Notify the user about the outcome and provide an appeal option."""
        user = discord.utils.get(guild.members, name=user_name)
        if user:
            try:
                msg = (
                    f"Your message was reviewed by moderators. Outcome: {outcome}.\n\n"
                    f"Original Message:\n{original_message}\n\n"
                    f"Reason: {explanation}\n\n"
                    "If you believe this was a mistake, you may reply to this message to appeal. "
                    "Would you like to appeal this decision?\n1. Yes\n2. No"
                )
                await user.send(msg)

                # Track pending appeal
                if user.id not in self.pending_appeals:
                    self.pending_appeals[user.id] = []
                self.pending_appeals[user.id].append({
                    'guild_id': guild.id,
                    'reported_name': user_name,
                    'outcome': outcome,
                    'original_message': original_message,
                    'explanation': explanation
                })

                # Initialize appeal confirmation state
                if not hasattr(self, 'awaiting_appeal_confirmation'):
                    self.awaiting_appeal_confirmation = {}
                self.awaiting_appeal_confirmation[user.id] = True

            except Exception as e:
                print(f"Failed to DM user {user_name}: {e}")

    async def notify_user_of_appeal_option(self, user_name, guild, explanation):
        """Notify the user about the appeal process after their post is removed."""
        user = discord.utils.get(guild.members, name=user_name)
        if user:
            try:
                msg = f"Your post was removed for the following reason: {explanation}.\n"
                msg += "If you believe this was a mistake, you can appeal by replying with your reason."
                await user.send(msg)
            except Exception as e:
                print(f"Failed to notify user {user_name}: {e}")

    async def handle_mod_channel_message(self, message):
        if not self.active_mod_flow:
            return
        step = self.active_mod_flow['step']
        content = message.content.strip().lower()
        mod_channel = message.channel
        guild = mod_channel.guild if hasattr(mod_channel, 'guild') else None

        if step == 'appeal_review':
            # Pull the info dict that was stashed earlier
            info = self.active_mod_flow.get('info', {})
            reported_name = info.get('reported_name')

            # Look up the User object in this guild
            reported_user = discord.utils.get(guild.members, name=reported_name)
            user_id = reported_user.id if reported_user else None

            # 1) Pop this appeal out of the queue
            if user_id in self.pending_appeals:
                self.pending_appeals[user_id].pop(0)
                if not self.pending_appeals[user_id]:
                    del self.pending_appeals[user_id]

            # 2) Send the DM back to the user with the moderator's decision
            if content == '1':  # ACCEPT
                await mod_channel.send("The appeal has been accepted. The original decision has been overturned.")
                if reported_user:
                    await reported_user.send(
                        "Your appeal has been accepted. The original decision has been overturned."
                    )

            elif content == '2':  # UPHOLD
                await mod_channel.send("The appeal has been reviewed and the original decision is upheld.")
                if reported_user:
                    await reported_user.send(
                        "Your appeal has been reviewed, and the original decision is upheld."
                    )

            else:
                await mod_channel.send("Invalid response. Please respond with:\n1. ACCEPT\n2. UPHOLD")
                return

            # Clear this flow
            self.active_mod_flow = None

            # 3) If that user still has more pending appeals, prompt them again
            if user_id in self.pending_appeals and self.pending_appeals[user_id]:
                next_info = self.pending_appeals[user_id][0]
                try:
                    prompt_text = (
                        f"Your message was reviewed by moderators. Outcome: {next_info['outcome']}.\n\n"
                        f"Original Message:\n{next_info['original_message']}\n\n"
                    )
                    if next_info.get('explanation'):
                        prompt_text += f"Reason: {next_info['explanation']}\n\n"
                    prompt_text += (
                       "If you believe this was a mistake, you may reply to this message to appeal. "
                        "Would you like to appeal this decision?\n1. Yes\n2. No"
                    )
                    await reported_user.send(prompt_text)
                    self.awaiting_appeal_confirmation[user_id] = True
                except Exception:
                    pass
            return

        ctx = self.active_mod_flow.get('context', {})
        report_type = self.active_mod_flow['report_type']
        report_content = self.active_mod_flow['report_content']
        reported_user_name = self.active_mod_flow['message_author']

        if step == 'confirm_danger_level':
            if content == '1':  # Moderator agrees with LLM
                predicted = ctx.get('predicted_danger', 'medium')
                ctx['danger_level'] = predicted

                # Now ask LLM to recommend a post‐action
                post_action = await self.classify_post_action(
                    report_content,
                    predicted,
                    self.active_mod_flow.get('user_context')
                )
                ctx['predicted_post_action'] = post_action  # e.g. "remove", etc.

                label_map = {
                    "do_not_recommend":     "DO NOT RECOMMEND",
                    "flag_as_unproven":      "FLAG AS UNPROVEN",
                    "remove":               "REMOVE",
                    "raise":                "RAISE",
                    "report_to_authorities": "REPORT TO AUTHORITIES"
                }
                action_label = label_map.get(post_action, None)

                if action_label:
                    await mod_channel.send(
                        f"System suggests post action: {action_label}. Do you agree?\n"
                        "1. Yes\n"
                        "2. No"
                    )
                    self.active_mod_flow['step'] = 'confirm_post_action'
                    return
                else:
                    # If LLM failed to return a valid post‐action, fall back to manual
                    if predicted == 'low':
                        await mod_channel.send(
                            "Predicted LOW danger. After claim is investigated, what action should be taken on post?\n"
                            "1. DO NOT RECOMMEND\n"
                            "2. FLAG AS UNPROVEN"
                        )
                        self.active_mod_flow['step'] = 'low_action_on_post'
                        return
                    else:
                        await mod_channel.send(
                            f"Predicted {predicted.upper()} danger. After claim is investigated, what action should be taken on post?\n"
                            "1. REMOVE\n"
                            "2. RAISE\n"
                            "3. REPORT TO AUTHORITIES"
                        )
                        self.active_mod_flow['step'] = ('medium_action_on_post'
                            if predicted == 'medium' else 'high_action_on_post')
                        return

            if content == '2':  # Moderator disagrees with LLM’s danger‐level
                await mod_channel.send(
                    "What is the level of danger for this report?\n"
                    "1. LOW\n"
                    "2. MEDIUM\n"
                    "3. HIGH"
                )
                self.active_mod_flow['step'] = 'danger_level_manual'
                return

            await mod_channel.send("Invalid response. Please reply with:\n1. Yes\n2. No")
            return

        if step == 'danger_level_manual':
            if content not in ['1','2','3']:
                await mod_channel.send("Invalid option. Please choose:\n1. LOW\n2. MEDIUM\n3. HIGH")
                return

            levels = {'1':'low','2':'medium','3':'high'}
            chosen = levels[content]
            ctx['danger_level'] = chosen

            # Ask LLM to recommend a post‐action given the manually chosen danger level:
            predicted_action = await self.classify_post_action(
                report_content,
                chosen,
                self.active_mod_flow.get('user_context')
            )
            ctx['predicted_post_action'] = predicted_action

            label_map = {
                "do_not_recommend":     "DO NOT RECOMMEND",
                "flag_as_unproven":      "FLAG AS UNPROVEN",
                "remove":               "REMOVE",
                "raise":                "RAISE",
                "report_to_authorities": "REPORT TO AUTHORITIES"
            }
            action_label = label_map.get(predicted_action, None)

            if action_label:
                await mod_channel.send(
                    f"System suggests post action: {action_label}. Do you agree?\n"
                    "1. Yes\n"
                    "2. No"
                )
                self.active_mod_flow['step'] = 'confirm_post_action'
            else:
                # Fallback if LLM failed to return a valid post‐action:
                if chosen == 'low':
                    await mod_channel.send(
                        "Predicted LOW danger. After claim is investigated, what action should be taken on post?\n"
                        "1. DO NOT RECOMMEND\n"
                        "2. FLAG AS UNPROVEN"
                    )
                    self.active_mod_flow['step'] = 'low_action_on_post'
                else:
                    await mod_channel.send(
                        f"Predicted {chosen.upper()} danger. After claim is investigated, what action should be taken on post?\n"
                        "1. REMOVE\n"
                        "2. RAISE\n"
                        "3. REPORT TO AUTHORITIES"
                    )
                    self.active_mod_flow['step'] = (
                        'medium_action_on_post' if chosen == 'medium' else 'high_action_on_post'
                    )
            return

        if step == 'confirm_post_action':
            if content == '1':  # Mod agrees with LLM’s post‐action
                post_action = ctx.get('predicted_post_action')
                danger = ctx.get('danger_level')
                # Retrieve the reported User object
                reported_user = discord.utils.get(guild.members, name=reported_user_name)

                # LOW‐danger branches
                if danger == 'low':
                    if post_action == 'do_not_recommend':
                        await mod_channel.send(
                            "Post will not be recommended. Action recorded. "
                            "(Update algorithm so post is not recommended.)"
                        )
                        self.user_stats.add_report(
                            reported_user.id,
                            report_type,
                            report_content,
                            "Post not recommended"
                        )
                        await self.notify_reported_user(
                            reported_user_name, guild,
                            outcome="Post not recommended."
                        )
                        self.active_mod_flow = None
                        return

                    elif post_action == 'flag_as_unproven':
                        await mod_channel.send(
                            "System suggests FLAG AS UNPROVEN. "
                            "Please add explanation for why post is being flagged."
                        )
                        self.active_mod_flow['step'] = 'flag_explanation'
                        return

                # MEDIUM/HIGH‐danger branches
                else:
                    if post_action == 'remove':
                        await mod_channel.send(
                            "System suggests REMOVE. Please add explanation for why post is being removed."
                        )
                        self.active_mod_flow['step'] = 'remove_explanation'
                        return

                    elif post_action == 'raise':
                        await mod_channel.send(
                            "System suggests RAISE to higher level moderator. "
                            "Report sent to higher level moderators."
                        )
                        self.user_stats.add_report(
                            reported_user.id,
                            report_type,
                            report_content,
                            "Report raised to higher level moderator"
                        )
                        self.active_mod_flow = None
                        return

                    elif post_action == 'report_to_authorities':
                        await mod_channel.send(
                            "System suggests REPORT TO AUTHORITIES. Report sent to authorities."
                        )
                        self.user_stats.add_report(
                            reported_user.id,
                            report_type,
                            report_content,
                            "Reported to authorities"
                        )
                        self.active_mod_flow = None
                        return

                # Fallback if LLM recommendation is invalid
                await mod_channel.send("Could not interpret recommended post action. Please choose manually.")
                danger = ctx.get('danger_level')
                if danger == 'low':
                    await mod_channel.send(
                        "After claim is investigated, what action should be taken on post?\n"
                        "1. DO NOT RECOMMEND\n"
                        "2. FLAG AS UNPROVEN"
                    )
                    self.active_mod_flow['step'] = 'low_action_on_post'
                else:
                    await mod_channel.send(
                        "After claim is investigated, what action should be taken on post?\n"
                        "1. REMOVE\n"
                        "2. RAISE\n"
                        "3. REPORT TO AUTHORITIES"
                    )
                    self.active_mod_flow['step'] = (
                        'medium_action_on_post' if danger == 'medium' else 'high_action_on_post'
                    )
                return

            if content == '2':  # Mod overrides–go manual
                danger = ctx.get('danger_level')
                if danger == 'low':
                    await mod_channel.send(
                        "What action should be taken on post?\n"
                        "1. DO NOT RECOMMEND\n"
                        "2. FLAG AS UNPROVEN"
                    )
                    self.active_mod_flow['step'] = 'low_action_on_post'
                else:
                    await mod_channel.send(
                        "What action should be taken on post?\n"
                        "1. REMOVE\n"
                        "2. RAISE\n"
                        "3. REPORT TO AUTHORITIES"
                    )
                    self.active_mod_flow['step'] = (
                        'medium_action_on_post' if danger == 'medium' else 'high_action_on_post'
                    )
                return

            await mod_channel.send("Invalid response. Please reply with:\n1. Yes\n2. No")
            return

        if step == 'confirm_user_action':
            if content == '1':  # Mod agrees with LLM’s user‐action
                user_action = ctx.get('predicted_user_action')
                reported_user = discord.utils.get(guild.members, name=reported_user_name)

                if user_action == 'record_incident':
                    await mod_channel.send("Incident recorded for internal use. (Add to internal incident count for user.)")
                    self.user_stats.add_report(
                        reported_user.id,
                        report_type,
                        report_content,
                        "Post removed and incident recorded",
                        ctx.get('remove_explanation', '')
                    )
                    self.active_mod_flow = None
                    return

                elif user_action == 'temporarily_mute':
                    await mod_channel.send("User will be muted for 24 hours.")
                    self.user_stats.add_report(
                        reported_user.id,
                        report_type,
                        report_content,
                        "Post removed and user temporarily muted",
                        ctx.get('remove_explanation', '')
                    )
                    await self.notify_reported_user(
                        reported_user_name,
                        guild,
                        outcome="You have been temporarily muted.",
                        explanation="You violated the community guidelines.",
                        original_message=report_content
                    )
                    self.active_mod_flow = None
                    return

                elif user_action == 'remove_user':
                    await mod_channel.send("User will be removed.")
                    self.user_stats.add_report(
                        reported_user.id,
                        report_type,
                        report_content,
                        "Post removed and user removed",
                        ctx.get('remove_explanation', '')
                    )
                    await self.notify_reported_user(
                        reported_user_name,
                        guild,
                        outcome="You have been removed from the server.",
                        explanation="You violated the community guidelines.",
                        original_message=report_content
                    )
                    # Track for appeal if removed
                    user_obj = reported_user
                    if user_obj:
                        if user_obj.id not in self.pending_appeals:
                            self.pending_appeals[user_obj.id] = []
                        self.pending_appeals[user_obj.id].append({
                            'guild_id': guild.id,
                            'reported_name': reported_user_name,
                            'outcome': "You have been removed from the server.",
                            'original_message': report_content,
                            'explanation': "You violated the community guidelines."
                        })
                    self.active_mod_flow = None
                    return

                # Fallback to manual if LLM output was unexpected
                await mod_channel.send(
                    "Could not interpret recommended user action. Please choose manually:\n"
                    "1. RECORD INCIDENT\n"
                    "2. TEMPORARILY MUTE\n"
                    "3. REMOVE USER"
                )
                self.active_mod_flow['step'] = 'action_on_user'
                return

            if content == '2':  # Mod overrides → manual user‐action
                await mod_channel.send(
                    "What action should be taken on the creator of the post?\n"
                    "1. RECORD INCIDENT\n"
                    "2. TEMPORARILY MUTE\n"
                    "3. REMOVE USER"
                )
                self.active_mod_flow['step'] = 'action_on_user'
                return

            await mod_channel.send("Invalid response. Please reply with:\n1. Yes\n2. No")
            return

        ctx = self.active_mod_flow['context']
        report_type = self.active_mod_flow['report_type']
        report_content = self.active_mod_flow['report_content']
        reported_user_name = self.active_mod_flow['message_author']

        # Get the user ID from the reported user's name
        reported_user = discord.utils.get(guild.members, name=reported_user_name)
        if not reported_user:
            await mod_channel.send(f"Could not find user {reported_user_name}. Please verify the username is correct.")
            return

        # Misinformation moderation flow
        if step == 'advertising_done':
            # Already handled
            self.active_mod_flow = None
            return
        if step == 'low_action_on_post':
            if content not in ['1', '2']:
                await mod_channel.send("Invalid option. Please choose:\n1. DO NOT RECOMMEND\n2. FLAG AS UNPROVEN")
                return
            if content == '1':  # DO NOT RECOMMEND
                await mod_channel.send("Post will not be recommended. Action recorded. (Update algorithm so post is not recommended.)")
                await self.notify_reported_user(reported_user_name, guild, outcome="Post not recommended.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post not recommended"
                )
                self.active_mod_flow = None
                return
            elif content == '2':  # FLAG AS UNPROVEN
                await mod_channel.send("Post will be flagged as unproven/non-scientific. Please add explanation for why post is being flagged.")
                self.active_mod_flow['step'] = 'flag_explanation'
                return
        if step == 'flag_explanation':
            await mod_channel.send(f"Explanation recorded: {message.content}\nFlagged post as not proven.")
            await self.notify_reported_user(reported_user_name, guild, outcome="Post flagged as unproven/non-scientific.", explanation=message.content)
            self.user_stats.add_report(
                reported_user.id,
                report_type,
                report_content,
                "Post flagged as unproven/non-scientific",
                message.content
            )
            self.active_mod_flow = None
            return
        if step == 'medium_action_on_post' or step == 'high_action_on_post':
            if content not in ['1', '2', '3']:
                await mod_channel.send("Invalid option. Please choose:\n1. REMOVE\n2. RAISE\n3. REPORT TO AUTHORITIES")
                return
            if content == '1':  # REMOVE
                await mod_channel.send("Post will be removed. Please add explanation for why post is being removed.")
                self.active_mod_flow['step'] = 'remove_explanation'
                return
            elif content == '2':  # RAISE
                await mod_channel.send("Raising to higher level moderator. Report sent to higher level moderators.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Report raised to higher level moderator"
                )
                self.active_mod_flow = None
                return
            elif content == '3':  # REPORT TO AUTHORITIES
                await mod_channel.send("Reporting to authorities. Report sent to authorities.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Reported to authorities"
                )
                self.active_mod_flow = None
                return
        if step == 'remove_explanation':
            explanation = message.content
            ctx['remove_explanation'] = explanation

            # Notify user that their post was removed
            await self.notify_reported_user(
                reported_user_name,
                guild,
                outcome="Post removed.",
                explanation=explanation,
                original_message=report_content
            )

            # 1) Let LLM recommend a user‐action now that post is removed
            recommended = await self.classify_user_action(
                report_content,
                ctx.get('danger_level', 'medium'),
                'remove',
                self.active_mod_flow.get('user_context')
            )
            ctx['predicted_user_action'] = recommended

            label_map = {
                "record_incident":   "RECORD INCIDENT",
                "temporarily_mute":  "TEMPORARILY MUTE",
                "remove_user":       "REMOVE USER"
            }
            action_label = label_map.get(recommended, None)

            if action_label:
                await mod_channel.send(
                    f"System suggests user action: {action_label}. Do you agree?\n"
                    "1. Yes\n"
                    "2. No"
                )
                self.active_mod_flow['step'] = 'confirm_user_action'
                return
            else:
                # If LLM failed, fall back to manual:
                await mod_channel.send(
                    "What action should be taken on the creator of the post?\n"
                    "1. RECORD INCIDENT\n"
                    "2. TEMPORARILY MUTE\n"
                    "3. REMOVE USER"
                )
                self.active_mod_flow['step'] = 'action_on_user'
                return
        if step == 'action_on_user':
            if content not in ['1', '2', '3']:
                await mod_channel.send("Invalid option. Please choose:\n1. RECORD INCIDENT\n2. TEMPORARILY MUTE\n3. REMOVE USER")
                return
            if content == '1':  # RECORD INCIDENT
                await mod_channel.send("Incident recorded for internal use. (Add to internal incident count for user.)")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post removed and incident recorded",
                    ctx.get('remove_explanation', '')
                )
                self.active_mod_flow = None
                return
            elif content == '2':  # TEMPORARILY MUTE
                await mod_channel.send("User will be muted for 24 hours.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post removed and user temporarily muted",
                    ctx.get('remove_explanation', '')
                )
                await self.notify_reported_user(
                    reported_user_name,
                    guild,
                    outcome="You have been temporarily muted.",
                    explanation="You violated the community guidelines.",
                    original_message=report_content
                )
                self.active_mod_flow = None
                return
            elif content == '3':  # REMOVE USER
                await mod_channel.send("User will be removed.")
                self.user_stats.add_report(
                    reported_user.id,
                    report_type,
                    report_content,
                    "Post removed and user removed",
                    ctx.get('remove_explanation', '')
                )
                await self.notify_reported_user(
                    reported_user_name,
                    guild,
                    outcome="You have been removed from the server.",
                    explanation="You violated the community guidelines.",
                    original_message=report_content
                )
                user = discord.utils.get(guild.members, name=reported_user_name)
                if user:
                    # Track for incoming DM in pending_appeals
                    if user.id not in self.pending_appeals:
                        self.pending_appeals[user.id] = []
                    self.pending_appeals[user.id].append({
                        'guild_id': guild.id,
                        'reported_name': reported_user_name,
                        'outcome': "You have been removed from the server.",
                        'original_message': report_content,
                        'explanation': "You violated the community guidelines."
                    })
                self.active_mod_flow = None
                return
    
    async def classify_abuse_type(self, message_content, user_context=None):
        system_prompt = (
            "You are a content moderation assistant. Your job is to classify messages into one of the following top-level abuse types: "
            "BULLYING, SUICIDE/SELF-HARM, SEXUALLY EXPLICIT/NUDITY, MISINFORMATION, HATE SPEECH, or DANGER.\n\n"
            "If the abuse type is MISINFORMATION, you must specify the misinformation category as:\n"
            "- HEALTH (with one of these subcategories: EMERGENCY, MEDICAL RESEARCH, REPRODUCTIVE HEALTH, TREATMENTS, ALTERNATIVE MEDICINE)\n"
            "- ADVERTISEMENT\n"
            "- NEWS (with one of these subcategories: HISTORICAL, POLITICAL, SCIENTIFIC)\n\n"
            "Respond in this format exactly:\n"
            "- For general types: `BULLYING`, `HATE SPEECH`, etc.\n"
            "- For misinformation types: `HEALTH (EMERGENCY) MISINFORMATION`, `NEWS (POLITICAL) MISINFORMATION`, `ADVERTISEMENT MISINFORMATION`, etc.\n"
            "- If the message does not fit any of these categories, respond with: `UNKNOWN`\n\n"
            "Only return the final category label."
        )
        if user_context:
            user_prompt = f"User context: {user_context}\nMessage: {message_content}\n\nClassify the abuse type:"
        else:
            user_prompt = f"Message: {message_content}\n\nClassify the abuse type:"
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            abuse_type = response.choices[0].message.content.strip().upper()
            return abuse_type
        except Exception as e:
            print(f"Error classifying abuse type: {e}")
            return "UNKNOWN"
        
    def normalize_abuse_type(self, label):
        label = label.upper()
        if "MISINFORMATION" in label:
            # Handle misinformation categories
            if "HEALTH" in label:
                subcategory = re.search(r"\((.*?)\)", label)
                if subcategory:
                    return f"HEALTH MISINFO - {subcategory.group(1).upper()}"
                return "HEALTH MISINFO"
            if "ADVERTISEMENT" in label:
                return "ADVERTISING MISINFO"
            if "NEWS" in label:
                subcategory = re.search(r"\((.*?)\)", label)
                if subcategory:
                    return f"NEWS MISINFO - {subcategory.group(1).upper()}"
                return "NEWS MISINFO"
        # Handle general abuse types
        valid_labels = {
            "BULLYING": "BULLYING",
            "SUICIDE/SELF-HARM": "SUICIDE/SELF-HARM",
            "SEXUALLY EXPLICIT/NUDITY": "SEXUALLY EXPLICIT/NUDITY",
            "HATE SPEECH": "HATE SPEECH",
            "DANGER": "DANGER"
        }
        return valid_labels.get(label, None)
    
    async def classify_danger_level(self, report_content, user_context=None):
        system_prompt = (
            "You are a content moderation assistant. "
            "Given a single user post, classify how dangerous its misinformation is to real-world safety. "
            "Choose exactly one of: LOW, MEDIUM, or HIGH."
        )
        if user_context:
            user_prompt = f"User context: {user_context}\nPost: {report_content}\n\nClassify danger level:"
        else:
            user_prompt = f"Post: {report_content}\n\nClassify danger level:"
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            lvl = response.choices[0].message.content.strip().upper()
            if lvl in ("LOW", "MEDIUM", "HIGH"):
                return lvl.lower()
            return "medium"
        except Exception:
            return "medium"
        
    async def classify_post_action(self, report_content, danger_level, user_context=None):
        system_prompt = (
            "You are a content moderation assistant. "
            "Given a user post and its danger level (LOW, MEDIUM, or HIGH), "
            "recommend exactly one action to take on the post.\n"
            "- If danger is LOW, choose ONE of: DO NOT RECOMMEND or FLAG AS UNPROVEN.\n"
            "- If danger is MEDIUM or HIGH, choose ONE of: REMOVE, RAISE, or REPORT TO AUTHORITIES.\n"
            "Respond with exactly one of those labels."
        )
        if user_context:
            user_prompt = (
                f"User context: {user_context}\n"
                f"Post: {report_content}\n"
                f"Danger level: {danger_level.upper()}\n\n"
                "Recommended post action:"
            )
        else:
            user_prompt = (
                f"Post: {report_content}\n"
                f"Danger level: {danger_level.upper()}\n\n"
                "Recommended post action:"
            )
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ]
            )
            action = response.choices[0].message.content.strip().upper()
            mapping = {
                "DO NOT RECOMMEND":      "do_not_recommend",
                "FLAG AS UNPROVEN":       "flag_as_unproven",
                "REMOVE":                 "remove",
                "RAISE":                  "raise",
                "REPORT TO AUTHORITIES":  "report_to_authorities"
            }
            return mapping.get(action, None)
        except Exception:
            return None

    async def classify_user_action(self, report_content, danger_level, post_action, user_context=None):
        if post_action != "remove":
            return None

        system_prompt = (
            "You are a content moderation assistant. A post has been determined to be REMOVED. "
            "Recommend exactly one follow‐up action on the user:\n"
            "- RECORD INCIDENT\n"
            "- TEMPORARILY MUTE\n"
            "- REMOVE USER\n"
            "Respond with exactly one label."
        )
        if user_context:
            user_prompt = (
                f"User context: {user_context}\n"
                f"Post: {report_content}\n"
                f"Danger level: {danger_level.upper()}\n\n"
                "Recommended user action:"
            )
        else:
            user_prompt = (
                f"Post: {report_content}\n"
                f"Danger level: {danger_level.upper()}\n\n"
                "Recommended user action:"
            )
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ]
            )
            action = response.choices[0].message.content.strip().upper()
            mapping = {
                "RECORD INCIDENT":   "record_incident",
                "TEMPORARILY MUTE":  "temporarily_mute",
                "REMOVE USER":       "remove_user"
            }
            return mapping.get(action, None)
        except Exception:
            return None

    async def prompt_next_moderation_step(self, mod_channel):
        await mod_channel.send("Moderator, please review the report and respond with your decision.")

client = ModBot()
client.run(discord_token)