from enum import Enum, auto
import discord
import re
import asyncio


'''
This code implements a moderator review flow, mirroring the design in report.py
'''

class ReviewState(Enum):
    REVIEW_START = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_CLASSIFICATION_CONFIRMATION = auto()
    AWAITING_VIOLATION_CONFIRMATION = auto()
    AWAITING_REMOVAL_RECOMMENDATION = auto()
    AWAITING_USER_REMOVAL = auto()
    AWAITING_SECOND_REVIEW_DECISION = auto()
    AWAITING_CLASSIFY_TYPE = auto()
    AWAITING_SUBTYPE = auto()
    AWAITING_AI_CHECK = auto()
    AWAITING_IMAGE_MISLEAD = auto()
    REVIEW_COMPLETE = auto()

class Review:
    START_KEYWORD = "review"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, report):
        self.state = ReviewState.REVIEW_START
        self.client = client
        self.report = report
        self.message = report.message
        self.reported_message = None
        self.type_selected = report.type_selected
        self.subtype_selected = report.subtype_selected
        self.q1_response = None
        self.q2_response = None
        self.block_response = None

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = ReviewState.REVIEW_COMPLETE
            return ["Review cancelled."]
        
        if self.report and self.state == ReviewState.REVIEW_START:
            self.state = ReviewState.AWAITING_CLASSIFICATION_CONFIRMATION
            return [(
                f"This was reported as **{self.type_selected} → "
                f"{self.subtype_selected}**. Is that correct? (yes/no)"
            )]
        
        if self.state == ReviewState.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["Could not parse link"]
            guild = self.client.get_guild(int(m.group(1)))
            channel = guild.get_channel(int(m.group(2))) if guild else None

            self.state = ReviewState.AWAITING_CLASSIFICATION_CONFIRMATION
            
            return [
                f"Our system flagged this as **{self.classification or 'Unknown'}**. "
                "Is this classification accurate? (yes/no)"
            ]
        
        if self.state == ReviewState.AWAITING_CLASSIFICATION_CONFIRMATION:
            self.q1_response = message.content
            if message.content == 'yes':
                self.state = ReviewState.AWAITING_REMOVAL_RECOMMENDATION
                return [
                    "Based on automated review and your input, this looks like guideline violation. "
                    "Do you recommend this post be removed? (yes/no)"
                ]
            if message.content == 'no':
                self.state = ReviewState.AWAITING_VIOLATION_CONFIRMATION
                return [
                    "Does this post appear to violate our Community Guidelines? (yes/no)"
                ]
            return ["Please respond with `yes` or `no`. "]
        
        # 4a) If classification inaccurate → violation confirmation
        if self.state == ReviewState.AWAITING_VIOLATION_CONFIRMATION:
            if message.content == 'yes':
                # ask to reclassify
                cats = list(self.CATEGORIES.keys())
                self.category_map = {str(i+1): c for i,c in enumerate(cats)}
                numbered = '\n'.join([f"{i+1}. {c}" for i,c in enumerate(cats)])
                self.state = ReviewState.AWAITING_CLASSIFY_TYPE
                return [
                    "Please classify this post's abuse type:", numbered,
                    "Respond with the number."
                ]
            if message.content == 'no':
                self.state = ReviewState.REVIEW_COMPLETE
                return ["Thank you for completing this review. "]
            return ["Please respond with `yes` or `no`. "]
        # 4b) If classification accurate → removal recommendation
        if self.state == ReviewState.AWAITING_REMOVAL_RECOMMENDATION:
            self.q2_response = message.content
            if message.content == 'yes':
                self.state = ReviewState.AWAITING_USER_REMOVAL
                return [
                    "Do you recommend this user be removed from our platform? (yes/no)"
                ]
            if message.content == 'no':
                self.state = ReviewState.AWAITING_SECOND_REVIEW_DECISION
                return [
                    "Would you like to flag this for a second review? (yes/no)"
                ]
            return ["Please respond with `yes` or `no`. "]
        
        # 5) User removal recommendation
        if self.state == ReviewState.AWAITING_USER_REMOVAL:
            if message.content == 'yes':
                self.state = ReviewState.REVIEW_COMPLETE
                return [
                    "✅ User profile will be reviewed by Community Safety Team."
                ]
            if message.content == 'no':
                self.state = ReviewState.REVIEW_COMPLETE
                return ["Thank you for completing this review. "]
            return ["Please respond with `yes` or `no`. "]


        # 6) Flag for second review?
        if self.state == ReviewState.AWAITING_SECOND_REVIEW_DECISION:
            if message.content == 'yes':
                self.state = ReviewState.REVIEW_COMPLETE
                return ["🔄 This post has been flagged for second review. "]
            if message.content == 'no':
                self.state = ReviewState.REVIEW_COMPLETE
                return ["Thank you for completing this review. "]
            return ["Please respond with `yes` or `no`. "]
        
        # 7) Reclassification flow: choose category
        if self.state == ReviewState.AWAITING_CLASSIFY_TYPE:
            if message.content in self.category_map:
                self.classification = self.category_map[message.content]
                subs = self.CATEGORIES[self.classification]
                self.subtype_map = {str(i+1): s for i,s in enumerate(subs)}
                numbered = '\n'.join([f"{i+1}. {s}" for i,s in enumerate(subs)])
                self.state = ReviewState.AWAITING_SUBTYPE
                return [
                    f"Selected type: {self.classification}.",
                    "Choose a subtype:", numbered,
                    "Respond with the number."
                ]
            return ["Please choose a valid category number. "]
        
        # 8) Subtype selection
        if self.state == ReviewState.AWAITING_SUBTYPE:
            if message.content in self.subtype_map:
                self.subtype_selected = self.subtype_map[message.content]
                self.state = ReviewState.AWAITING_AI_CHECK
                return [
                    "Our system finds there's a __% chance the image was AI-generated or altered.",
                    "Could this image mislead or deceive our users? (yes/no)"
                ]
            return ["Please choose a valid subtype number. "]

        # 9) AI image check
        if self.state == ReviewState.AWAITING_AI_CHECK:
            if message.content in ('yes','no'):
                self.ai_confidence = message.content
                self.state = ReviewState.AWAITING_IMAGE_MISLEAD
                return ["Could this image mislead or deceive our users? (yes/no)"]
            return ["Please respond with `yes` or `no`. "]

        # 10) Image mislead decision
        if self.state == ReviewState.AWAITING_IMAGE_MISLEAD:
            if message.content in ('yes','no'):
                self.image_mislead = message.content
                self.state = ReviewState.REVIEW_COMPLETE
                return ["Thank you for completing this review. "]
            return ["Please respond with `yes` or `no`. "]

        return []
