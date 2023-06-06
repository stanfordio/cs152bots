from enum import Enum, auto
import discord
import re


#INFORM PLATFORM OF POTENTIAL COLLOQUIALISM
class Inform_State(Enum):
    INFORM_START = auto()
    AWAITING_COLL = auto()
    AWAITING_DESCRIPTION = auto()
    AWAITING_FIRST_EXAMPLE = auto()
    CONFIRMING_FIRST_EXAMPLE = auto()
    AWAITING_SECOND_EXAMPLE = auto()
    CONFIRMING_SECOND_EXAMPLE = auto()
    AWAITING_THIRD_EXAMPLE = auto()
    CONFIRMING_THIRD_EXAMPLE = auto()
    INFORM_COMPLETE = auto()
  

    MOD_START = auto()
    ADDITIONAL_ACTION = auto() 
    ADD_WORD = auto()
    NO_ACTION = auto()  
    
    POST_REMOVAL = auto()
    NOTIFY_OTHERS = auto()  
    REVIEW_OTHERS = auto()

    USER_BAN_DECISION = auto()  
    USER_BAN_DECISION_CONFIRM = auto()  
    NOTIFY_DECISION = auto()  
    


  
   


class Colloquialism:
    START_KEYWORD = "inform of colloquialism"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, informer_id, inform_id):
        self.state = Inform_State.INFORM_START
        self.client = client
        self.informer_id = informer_id
        self.colloquialism = None
        self.colloquialism_description = None
        self.first_example = None
        self.second_example = None
        self.third_example = None
        self.is_colloquialism = None

        self.message = None
        self.inform_id = inform_id

        self.mod_review = False
        self.guild = None


    
    
    async def handle_message(self, message):
        '''
        Handle message from user informing of potential colloquialism
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = Inform_State.INFORM_COMPLETE
            return ["Inform cancelled."]
        
        if self.state == Inform_State.INFORM_START:
            reply =  "Thank you for starting the colloquialism informing process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please enter the keyword you would like to nominate for inclusion to the open source colloquialsm list.\n"
            self.state = Inform_State.AWAITING_COLL
            return [reply]
            
        if self.state == Inform_State.AWAITING_COLL:
            self.colloquialism = message.content
            reply = "Please enter a description of the keyword and its intended purposes. Be as specific as possible.\n"
            self.state = Inform_State.AWAITING_DESCRIPTION
            return [reply]

        if self.state == Inform_State.AWAITING_DESCRIPTION:
            self.colloquialism_description = message.content
            reply = "Please enter the first example of the keyword in use.\n"
            self.state = Inform_State.AWAITING_FIRST_EXAMPLE
            return [reply]
        
        if self.state == Inform_State.AWAITING_FIRST_EXAMPLE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]


            self.first_example = message
            self.guild = guild
            reply = "I found this message:" + "```" + message.author.name + ": " + message.content + "```"
            reply += "If this is correct, please input 1. Otherwise, please input 2.\n"
            self.state = Inform_State.CONFIRMING_FIRST_EXAMPLE
            return [reply]
        
        if self.state == Inform_State.CONFIRMING_FIRST_EXAMPLE:
            if message.content == '1':
                reply = "Please enter the second example of the keyword in use.\n"
                self.state = Inform_State.AWAITING_SECOND_EXAMPLE
                return [reply]
            elif message.content == '2':
                reply = "Please enter the first example of the keyword in use.\n"
                self.state = Inform_State.AWAITING_FIRST_EXAMPLE
                return [reply]
            else:
                reply = "I'm sorry, but I don't recognize that input. Please enter 1 or 2."
                return [reply]
            
        if self.state == Inform_State.AWAITING_SECOND_EXAMPLE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]


            self.second_example = message
            self.guild = guild
            reply = "I found this message:" + "```" + message.author.name + ": " + message.content + "```"
            reply += "If this is correct, please input 1. Otherwise, please input 2.\n"
            self.state = Inform_State.CONFIRMING_SECOND_EXAMPLE
            return [reply]
        
        if self.state == Inform_State.CONFIRMING_SECOND_EXAMPLE:
            if message.content == '1':
                reply = "Please enter the third example of the keyword in use.\n"
                self.state = Inform_State.AWAITING_THIRD_EXAMPLE
                return [reply]
            elif message.content == '2':
                reply = "Please enter the second example of the keyword in use.\n"
                self.state = Inform_State.AWAITING_SECOND_EXAMPLE
                return [reply]
            else:
                reply = "I'm sorry, but I don't recognize that input. Please enter 1 or 2."
                return [reply]
            
        if self.state == Inform_State.AWAITING_THIRD_EXAMPLE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]


            self.third_example = message
            self.guild = guild
            reply = "I found this message:" + "```" + message.author.name + ": " + message.content + "```"
            reply += "If this is correct, please input 1. Otherwise, please input 2.\n"
            self.state = Inform_State.CONFIRMING_THIRD_EXAMPLE
            return [reply]
        
        if self.state == Inform_State.CONFIRMING_THIRD_EXAMPLE:
            if message.content == '1':
                reply = "Thank you for your submission. We will review it and get back to you.\n"
                self.state = Inform_State.MOD_START
                self.mod_review = True
                self.is_colloquialism = True
                return [reply]
            elif message.content == '2':
                reply = "Please enter the third example of the keyword in use.\n"
                self.state = Inform_State.AWAITING_THIRD_EXAMPLE
                return [reply]
            else:
                reply = "I'm sorry, but I don't recognize that input. Please enter 1 or 2."
                return [reply]

    async def mod_flow(self, message):  
        if self.state == Inform_State.MOD_START:
            if not self.is_colloquialism:
                reply = f"Report from user: {self.informer_id}. Not a prospective new colloquialism. This is the end of the process"
                self.state = Inform_State.INFORM_COMPLETE
                return [reply]

            reply =  "We have received the following moderation request:\n"
            reply += f"User filing report: {self.informer_id}\n"
            reply += f"Colloquialism: {self.colloquialism}\n"
            reply += f"Colloquialism description: {self.colloquialism_description}\n"
            reply += f"Example 1: " + "```" + self.first_example.author.name + ": " + self.first_example.content + "```\n"
            reply += f"Example 2: " + "```" + self.second_example.author.name + ": " + self.second_example.content + "```\n"
            reply += f"Example 3: " + "```" + self.third_example.author.name + ": " + self.third_example.content + "```\n"
            reply += f"Is this a colloquialism?\n"
            reply += f"\n INFORM_ID: {self.inform_id}\n"
            reply += f"`{self.inform_id}:1`: Yes\n"
            reply += f"`{self.inform_id}:2`: No\n"
            self.state = Inform_State.ADDITIONAL_ACTION
            return [reply]
              
        if self.state == Inform_State.ADDITIONAL_ACTION:
            reply = f"I'm sorry, but I don't recognize that input. Please enter {self.inform_id}:1 or {self.inform_id}:2"
            if message.content == f'{self.inform_id}:1':
                reply = "Keyword added to colloquialism list. Please add comments explaining your decision to the informer/for cataloguing purposes."
                #add self.colloquialism to colloquialisms.txt file in a new line
                with open("colloquialisms.txt", "a") as f:
                    f.write(self.colloquialism + "\n")
                self.state = Inform_State.ADD_WORD
                return [reply]
            elif message.content == f'{self.inform_id}:2':
                reply = "No action taken. Please add comments explaining your decision to the informer/for cataloguing purposes.\n"
                self.state = Inform_State.NO_ACTION
                return [reply]
            return [reply]
        
        if self.state == Inform_State.ADD_WORD:
            self.moderator_response = message.content
            reply = "Thank you. Review complete."
            self.state = Inform_State.INFORM_COMPLETE
            return [reply]

        if self.state == Inform_State.NO_ACTION:
            self.moderator_response = message.content
            reply = "Thank you. Review complete."
            self.state = Inform_State.INFORM_COMPLETE
            return [reply]

            
    def inform_complete(self):
        return self.state == Inform_State.INFORM_COMPLETE
