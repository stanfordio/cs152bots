from enum import Enum, auto
import discord
import re

# OPTIONS_MESSAGE_1 = 'Is this a deep fake with a person in it? Please respond with yes or no.'
OPTIONS_MESSAGE_2 = 'Please select the category that best reflects the image and message content:\n'
# OPTIONS_MESSAGE_2 += '1. Satire, memes, political commentary\n2. Disinformation\n3. Nudity/Graphic\n4. Imminent danger\n5. Financial Spam\n6. Other spam\n7. Hate speech/harassment\n8. Other'
OPTIONS_MESSAGE_2 += 'You can select from\n1. Imminent Danger\n2. Spam (financial or other) \n3. Nude or Graphic Media\n4. Disinformation\n5. Hate speech/harrassment\n6. Other (including satire, memes, commentary, couterspeech, etc.)\nPlease type the number of the content type you see.\nIf the image has no people in it or is not harmful, then please press 6'

NUDITY_OPTIONS_MESSAGE = 'Is this content\n1. Of you (revenge porn, sextortion, etc)\n2. Of a minor\n3. Used for harassment\n4. Other'
SPAM_OPTIONS_MESSAGE = 'Is this content\n1. Financial spam\n2. Other spam'

END_MESSAGE = 'This content is considered within the rules of the server. This report is considered processed and done!'

# these are displayed at the end of moderator reports for everything except for nudity report
BOT_ACTIONS = {
    # 1: ['Flagged content as AI generated. This report is considered processed and done!'],
    4: ['Flagged content as AI generated. This report is considered processed and done!'],
    5: ['Flagged content as AI generated, and the author of the content has been assigned a strike. This report is considered processed and done!'],
    1: ['The content has been removed and the authorities have been notified. This report is considered processed and done!'],
    # 6: ['The content has been removed and the author has been assigned a strike. This report is considered processed and done!'],
    # 5: ['The content has been removed, the user has been banned, and the authorities have been notified. This report is considered processed and done!'],
    6: ['This content is considered within the rules of the server. This report is considered processed and done!'],
}

# these are displayed at the end of moderator reports for nudity reports
NUDITY_MESSAGE = {
    1: ['This content has been removed, and the authorities have been notified. This report is considered processed and done!'],
    2: ['This content has been removed, the author has been banned, and the authorities have been notified. This report is considered processed and done!'],
    3: ['This content has been removed, and the author of the content has been assigned a strike. This report is considered processed and done!'],
    4: ['This content is considered within the rules of the serve, and has been blurred. This report is considered processed and done!'],
}

SPAM_MESSAGE = {
    1: ['This content has been removed, the author has been banned, and the authorities have been notified. This report is considered processed and done!'],
    2: ['The content has been removed and the author has been assigned a strike. This report is considered processed and done!'],
}

class State(Enum):
    REPORT_START = auto()
    AWAITING_COMMAND = auto()
    # AWAITING_PEOPLE_STATE = auto()
    AWAITING_ABUSE_TYPE = auto()
    NUDITY_FLOW = auto()
    
    REPORT_COMPLETE = auto()
    # MESSAGE_IDENTIFIED = auto()
    # REPORT_COMPLETE = auto()
    
    # AWAIT_CONTENT_TYPE = auto()
    # AWAIT_SPECIFIC_TYPE = auto()
    
    # AWAIT_AI_REMOVAL = auto()
    
class ModReport:
    START_KEYWORD = 'start'
    CANCEL_KEYWORD = 'cancel'
    HELP_KEYWORD = 'help'
    
    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        
        # 1 is Imminent Danger, 2 is Spam, 3 is Nudity or Graphic, 4 is Disinformation, 5 is Hate speech/harrassment, 6 is Other
        self.abuse_type = None
        self.requires_forwarding = False
        self.forward_abuse_string = '' #used to detail the first level abuse
        self.specific_abuse_string = ''#used to detail the second level abuse
        self.keep_AI = True
        
        self.report_no = None
    
    async def handle_message(self, message, awaiting_mod_dict, caseno_to_info, most_recent):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report processing cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the moderator review process. "
            reply += "Say `help` at any time for more information.\n\n"
            if not caseno_to_info:
                reply += "No cases have been reported yet."
            else:
                reply += "Please type `RETRIEVE` followed by a case number, `MOST RECENT`, or `HIGH PRIORITY` to retrieve a case."
                self.state = State.AWAITING_COMMAND
            return [reply]

        message_content = message.content.split()
            
        if message_content[0].lower() == ModReport.HELP_KEYWORD:
            return ['Please type `RETRIEVE` followed by a case number, `MOST RECENT`, or `HIGH PRIORITY` to retrieve a case.']
        
        if self.state == State.AWAITING_COMMAND:
            
            
            if message_content[0].upper() != 'RETRIEVE':
                return_message = 'Invalid command. Please type RETRIEVE followed by a case number, \'MOST RECENT\' or \'HIGH PRIORITY\' to retrieve a case or EXECUTE followed by a case number, target, and action to close a case.'
                # await message.channel.send(return_message)
                return [return_message]
            
            elif len(message_content) == 1:
                return ['Please type a case number, \'MOST RECENT\', or \'HIGH PRIORITY\' to retrieve a case.']
            
            elif message_content[0].upper() == 'RETRIEVE' and 'MOST RECENT' not in message.content.upper() and 'HIGH PRIORITY' not in message.content.upper():
                try:
                    self.state = State.AWAITING_PEOPLE_STATE
                    case_number = int(message_content[1])
                    case_number = '#' + str(case_number)
                    if case_number in caseno_to_info:
                        package = caseno_to_info[case_number]
                        self.report_no = package[-1]
                        out = []
                        out.append(package[0])
                        if package[1]:
                            out.append(await package[1].to_file())
                        out.append(package[2])
                        # out.append(OPTIONS_MESSAGE_1)
                        return out
                    else:
                        return ['Case not found.']
                except:
                    return ['Invalid case number.']
            elif message_content[0].upper() == 'RETRIEVE' and 'MOST RECENT' in message.content.upper():
                if most_recent:
                    self.state = State.AWAITING_ABUSE_TYPE
                    out = []
                    package = most_recent
                    self.report_no = package[-1]
                    out.append(package[0])
                    if package[1]:
                        out.append(await package[1].to_file())
                    out.append(package[2])
                    # out.append(OPTIONS_MESSAGE_1)
                    return out
                else:
                    return ['No cases found.']
            elif message_content[0].upper() == 'RETRIEVE' and 'HIGH PRIORITY' in message.content.upper():
                # abuse 1 and 2 are high priority, the rest are not
                for key in range(1, 3):
                    if awaiting_mod_dict[key]:
                        out = []
                        package = awaiting_mod_dict[key][min(awaiting_mod_dict[key].keys())]
                        self.report_no = package[-1]
                        self.state = State.AWAITING_ABUSE_TYPE
                        out.append(package[0])
                        if package[1]:
                            out.append(await package[1].to_file())
                        out.append(package[2])
                        # out.append(OPTIONS_MESSAGE_1)
                        return out
                else:
                    return ['No high priority cases found.']
        
        if self.state == State.AWAITING_ABUSE_TYPE:
            try:
                selection = int(message.content)
                self.abuse_type = selection
            except:
                return ["Please type the number of the content type you see."]
            
            if self.abuse_type not in BOT_ACTIONS:
                self.state = State.REPORT_COMPLETE
                curr_abuse = self.abuse_type
                if curr_abuse == 3:
                    self.state = State.NUDITY_FLOW
                    return [NUDITY_OPTIONS_MESSAGE]
                elif curr_abuse == 2:
                    self.state = State.NUDITY_FLOW
                    return [SPAM_OPTIONS_MESSAGE]
                return BOT_ACTIONS[curr_abuse]
            else:
                self.state = State.REPORT_COMPLETE
                curr_abuse = self.abuse_type
                return BOT_ACTIONS[curr_abuse]
        
        if self.state == State.NUDITY_FLOW:
            try:
                selection = int(message.content)
            except:
                return [NUDITY_OPTIONS_MESSAGE]
            
            if self.abuse_type == 3 and selection < 1 or selection > 4:
                return ["Please type a valid number of the content type you see."]
            elif self.abuse_type == 3:
                self.state = State.REPORT_COMPLETE
                return NUDITY_MESSAGE[selection]
            if self.abuse_type == 2 and selection < 1 or selection > 2:
                return ["Please type a valid number of the content type you see."]
            elif self.abuse_type == 2:
                self.state = State.REPORT_COMPLETE
                return SPAM_MESSAGE[selection]
            # self.state = State.REPORT_COMPLETE
            # return SPAM_MESSAGE[selection]
            
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
        

    
