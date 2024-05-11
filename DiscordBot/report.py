from enum import Enum, auto
import discord
import re


# options given to users to select from to make 
SPECIFIC_OPTIONS = {
    1: "Please select the type of imminent danger you see:\n1. Credible threat of violence\n 2. Suicidal content or self-harm",
    2: "Please select the type of spam you see:\n1. Fraud\n2. Solicitation\n3. Impersonation",
    3: "Please select the type of nudity or graphic content you see:\n1. Directed at you (e.g., porn, violence, sextortion)\n2. Directed at a minor\n3. Harassment\n4. Other",
    4: "Please select the type of disinformation you see:\n1. Targeted at political candidates/figures\n2. Imposter\n3. False context\n4. Fabricated content",
    5: "Please select the type of hate speech/harrassment you see:\n1. Bullying\n2. Hate speech directed at me/specific group of people\n3. Unwanted sexual content\n4. Revealing Private Information",
}

# closing messages given to the user, before their report is processed
CLOSING_MESSAGES = {
    1: ["Thank you for reporting. Our content moderation team will review the report and decide on the appropriate response, notifying local authorities if necessary."],
    2: ['Thank you for reporting. Our content moderation team will review the report and decide on the appropriate response, notifying local authorities if necessary.'],
    3: ['Thank you for reporting. Our content moderation team will review this report and will take appropriate steps to flag, censor,  or remove this content.'],
    4: ['Thank you for reporting. Our content moderation team will review the report and decide on the appropriate actions. This may include flagging of the content as AI-generated.\nWould you like us to remove all detected AI-generated content in from your feed the future?'],
    5: ['Thank you for reporting. Our content moderation team will review the report and decide on the appropriate actions. This may include flagging of the content as AI-generated.\nWould you like us to remove all detected AI-generated content in from your feed the future?'],
    6: ["Thank you for reporting. This content does not violate our policy as it does not cause significant confusion about the authenticity of the media."]
}


# for the first level response
ABUSE_STRINGS = {
    1: "Imminent Danger",
    2: "Spam",
    3: "Graphic Media or Nudity",
    4: "Disinformation",
    5: "Hate speech/harrassment",
    6: "Other"
}

# for the second level response
SPECIFIC_ABUSE_STRINGS = {
    1: ["Credible threat of violence", "Suicidal content or self-harm"],
    2: ["Fraud", "Solicitation", "Impersonation"],
    3: ["Of you (revenge porn or sextortion)", "Of a minor", 'Harassment', "Other"],
    4: ["Targeted at political candidates/figures", "Imposter", "False context", "Fabricated content"],
    5: ["Bullying", "Hate speech directed at me/specific group of people", "Unwanted sexual content", "Revealing Private Information"]
}

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    
    AWAIT_CONTENT_TYPE = auto()
    AWAIT_SPECIFIC_TYPE = auto()
    
    AWAIT_AI_REMOVAL = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    
    report_no = 0

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

        self.report_no = '#' + str(Report.report_no)
        Report.report_no += 1
        
        # 1 is Imminent Danger, 2 is Spam, 3 is Nudity or Graphic, 4 is Disinformation, 5 is Hate speech/harrassment, 6 is Other
        self.abuse_type = None
        self.requires_forwarding = False
        self.forward_abuse_string = '' #used to detail the first level abuse
        self.specific_abuse_string = ''#used to detail the second level abuse
        self.keep_AI = True
        
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            Report.report_no -= 1
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
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))

            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.AWAIT_CONTENT_TYPE
            self.message = message
            # return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #         "if you want to report, please specify the type of AI-generated content you see."] \
                
            out = ['Does the image contain any people? Do you think it is a deepfake and harmful? If so, please continue reading!\n']
            out +=    [' You can select from\n1. Imminent Danger\n2. Spam\n3. Nudity or Graphic\n4. Disinformation\n5. Hate speech/harrassment\n6. Other (including satire, memes, commentary, couterspeech, etc.)\n'] \
                            + ['Please type the number of the content type you see.\nIf the image has no people in it or is not harmful, then please press 6']
            
            
            return out

            
        # this block determines the type of abuse the user is reporting
        # for numbering see comments in init
        if self.state == State.AWAIT_CONTENT_TYPE:
            try:
                selection = int(message.content)
                self.abuse_type = selection
            except:
                return ["Please type the number of the content type you see."]
            
            if self.abuse_type not in SPECIFIC_OPTIONS:
                self.state = State.REPORT_COMPLETE
                curr_abuse = self.abuse_type
                # if curr_abuse == 3:
                #     self.requires_forwarding = True
                #     self.forward_abuse_string = ABUSE_STRINGS[curr_abuse]
                #     return CLOSING_MESSAGES[curr_abuse]
                if curr_abuse == 6:
                    self.requires_forwarding = True
                    self.forward_abuse_string = ABUSE_STRINGS[curr_abuse]
                    return CLOSING_MESSAGES[curr_abuse]
            else:
                self.state = State.AWAIT_SPECIFIC_TYPE
                return [SPECIFIC_OPTIONS[self.abuse_type]]

        # this block zones in on the specific type of abuse the user is reporting
        if self.state == State.AWAIT_SPECIFIC_TYPE:
            try:
                selection = int(message.content)
            except:
                return [SPECIFIC_OPTIONS[self.abuse_type]]
            
            if selection < 1 or (selection > 2 and self.abuse_type == 1) or (selection > 3 and self.abuse_type == 2 ) or (selection > 4 and self.abuse_type >=3):
                return ["Please type a valid number of the content type you see."]
            
            if self.abuse_type == 4 or self.abuse_type == 5:
                self.state = State.AWAIT_AI_REMOVAL
                curr_abuse = self.abuse_type

            else:
                self.state = State.REPORT_COMPLETE
                curr_abuse = self.abuse_type

            self.requires_forwarding = True
            self.forward_abuse_string = ABUSE_STRINGS[curr_abuse]
            self.specific_abuse_string = SPECIFIC_ABUSE_STRINGS[curr_abuse][selection-1]
            # implement for the specific abuse type
            return CLOSING_MESSAGES[curr_abuse]
            
        # this block implements the AI removal feature
        if self.state == State.AWAIT_AI_REMOVAL:
            try:
                selection = message.content.lower()
            except:
                return ["Please type yes or no."]
            
            self.state = State.REPORT_COMPLETE
            if selection == 'yes':
                self.keep_AI = False
            if selection == 'no':
                self.keep_AI = True
            
            return ['Done!']


        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

