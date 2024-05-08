from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    CONFIRMING_MESSAGE = auto()
    BLOCKING_MESSAGE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reported_message = None
        self.step = None
        self.abuse_type = None
        self.result = {}
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            reported_channel = guild.get_channel(int(m.group(2)))
            if not reported_channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                self.reported_message = await reported_channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            # if not all of these, then messeage exists, so let's confirm with the reporting party
            self.state = State.CONFIRMING_MESSAGE

        
        if self.state == State.CONFIRMING_MESSAGE:
            # ask the user to confirm if this is the message they wanted to report
            if self.abuse_type == None:
                confirmation_prompt = "I found this message:", "```" + self.reported_message.author.name + ": " + self.reported_message.content + "```", \
                    "Is this the message you want to report? (yes/no)"
                self.abuse_type = 0
                return [confirmation_prompt]
            

            if message.content.lower() not in ["yes", "no"]:
                self.abuse_type = 0
                return ["please respond appropraitely (ONLY yes or no)."]
            
            if message.content.lower() == "no":
                self.state = State.AWAITING_MESSAGE
                self.abuse_type = None
                return ["Sorry I couldn't retrieve the correct message. Could you please double check the link and resend it?"]

            if message.content.lower() == "yes":
                self.state = State.MESSAGE_IDENTIFIED
                self.result["Reported User"] = self.reported_message.author.name
                self.result["Reported Message"] = self.reported_message.content
                self.abuse_type = None

                    
        if self.state == State.MESSAGE_IDENTIFIED:
            if self.abuse_type == None:
                confirmed = "Thank you for confirming! Now let's answer a few questions to assist you effectively."
                reply = "Please select a reason for reporting this user (Enter corresponding number only):\n"
                options = [
                    "Sexual Content and Child Exploitation (I am a child and I feel uncomfortable)",
                    "Violence and Disturbing Content",
                    "Harassment and Harmful Behavior",
                    "Illegal and Misleading Activities"
                ]
                for i, option in enumerate(options, start=1):
                    reply += f"{i}. {option}\n"
                self.abuse_type = 1
                return [confirmed, reply]
            
            if self.abuse_type == 1:
                if message.content not in ['1', '2', '3', '4']:
                    return ["please enter only a valid number (1, 2, 3, 4)"]
                self.abuse_type = 2
                self.message = message

            # if  Sexual Content and Child Exploitation
            if self.message.content == "1":
                options = [
                        "Sextortion",
                        "Sexual Harassment",
                        "Child Sexual Exploitation or Abuse",
                        "I am a child and someone I don’t know is sending me strange messages",
                        "other"
                    ]
                if self.abuse_type == 2:
                    reply = "Please select from the following options (Enter corresponding number only):\n"
                    for i, option in enumerate(options, start=1):
                        reply += f"{i}. {option}\n"
                    self.abuse_type = 3
                    confirm = "You said 'Sexual Content and Child Exploitation (I am a child and I feel uncomfortable)' - I am deeply sorry about that.\n"
                    self.result["Abuse Type"] = "Sexual Content and Child Exploitation (I am a child and I feel uncomfortable)"
                    return [confirm, reply]
                if self.abuse_type == 3:
                    if message.content not in ['1', '2', '3', '4', '5']:
                        return ["please enter a valid number ONLY (1, 2, 3, 4, 5)"]
                    else:
                        self.result["Abuse Subsection"] = options[int(message.content)]
                        more_info = "Would you like to provide any additional context for our content moderation team to review? (Please share below if yes, else reply no) \n"
                        self.abuse_type = 4
                        return [more_info]
                    
                self.result["Additional Information"] = message.content
                
        # if Violence and Disturbing Content
            if self.message.content == "2":
                options = [
                    "Graphic Depictions of Violence",
                    "Gore and Mutilation",
                    "Self-harm or Suicide",
                    "Intent to cause real-life harm to person or property",
                    "other"
                    ]
                if self.abuse_type == 2:
                    reply = "Please select from the following options (Enter corresponding number only):\n"
                    for i, option in enumerate(options, start=1):
                        reply += f"{i}. {option}\n"
                    self.abuse_type = 3
                    confirm = "You said 'Violence and Disturbing Content' - I am deeply sorry about that.\n"
                    self.result["Abuse Type"] = "Violence and Disturbing Content"
                    return [confirm, reply]
                if self.abuse_type == 3:
                    if message.content not in ['1', '2', '3', '4', '5']:
                        return ["please enter a valid number ONLY (1, 2, 3, 4, 5)"]
                    else:
                        self.result["Abuse Subsection"] = options[int(message.content)]
                        more_info = "Would you like to provide any additional context for our content moderation team to review? (Please share below if yes, else reply no) \n"
                        self.abuse_type = 4
                        return [more_info]
                self.result["Additional Information"] = message.content
    
            # if Harassment and Harmful Behavior
            if self.message.content == "3":
                options = [
                    "Bullying",
                    "Cyberstalking, Doxxing, Threats",
                    "Hate Speech and Discrimination",
                    "Spam or Advertising",
                    "other"
                ]
                if self.abuse_type == 2:
                    reply = "Please select from the following options (Enter corresponding number only):\n"
                    for i, option in enumerate(options, start=1):
                        reply += f"{i}. {option}\n"
                    self.abuse_type = 3
                    confirm = "You said 'Harassment and Harmful Behavior' - I am deeply sorry about that.\n"
                    self.result["Abuse Type"] = "Harassment and Harmful Behavior"
                    return [confirm, reply]
                if self.abuse_type == 3:
                    if message.content not in ['1', '2', '3', '4', '5']:
                        return ["please enter a valid number ONLY (1, 2, 3, 4, 5)"]
                    else:
                        self.result["Abuse Subsection"] = options[int(message.content)]
                        more_info = "Would you like to provide any additional context for our content moderation team to review? (Please share below if yes, else reply no) \n"
                        self.abuse_type = 4
                        return [more_info]
                self.result["Additional Information"] = message.content

            # if Illegal and Misleading Activities
            if self.message.content == "4":
                options = [
                    "Fraud and Scams",
                    "Impersonation",
                    "other"
                    ]
                if self.abuse_type == 2:
                    reply = "Please select from the following options (Enter corresponding number only):\n"
                    for i, option in enumerate(options, start=1):
                        reply += f"{i}. {option}\n"
                    self.abuse_type = 3
                    confirm = "You said 'Illegal and Misleading Activities' - I am deeply sorry about that.\n"
                    self.result["Abuse Type"] = "Illegal and Misleading Activities"
                    return [confirm, reply]
                if self.abuse_type == 3:
                    if message.content not in ['1', '2', '3']:
                        return ["please enter a valid number ONLY (1, 2, 3)"]
                    else:
                        self.result["Abuse Subsection"] = options[int(message.content)]
                        more_info = "Would you like to provide any additional context for our content moderation team to review? (Please share below if yes, else reply no) \n"
                        self.abuse_type = 4
                        return [more_info]
                self.result["Additional Information"] = message.content

            
            info = "This is what we gathered: \n"
            for key, value in self.result.items():
                info += key + " : " + value + "\n"
            block = "\n In the meantime, do you want this user to be blocked (yes/no)?"
            self.state = State.BLOCKING_MESSAGE
            return ["Thank you for submitting a report.", info, "The content moderation team will review your submission soon.", block]

        if self.state == State.BLOCKING_MESSAGE:
            if message.content.lower() not in ["yes","no"]:
                return ["please respond appropriately (ONLY yes or no)"]
            else:
                self.state = State.REPORT_COMPLETE 
                if message.content.lower() == "yes":  
                    return ["Okay " + self.result["Reported User"] + " has been blocked. Stay safe and feel free to reach out again."]
                else:
                    return ["Okay " + self.result["Reported User"] + " will not be blocked. Stay safe and feel free to reach out again."]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
