from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_COMMAND = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    
    AWAIT_CONTENT_TYPE = auto()
    AWAIT_SPECIFIC_TYPE = auto()
    
    AWAIT_AI_REMOVAL = auto()
    
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
        
        if self.state == State.AWAITING_COMMAND:
            message_content = message.content.split()
            if message_content[0] != 'RETRIEVE' and message_content[0] != 'EXECUTE':
                return_message = 'Invalid command. Please type RETRIEVE followed by a case number, \'MOST RECENT\' or \'HIGH PRIORITY\' to retrieve a case or EXECUTE followed by a case number, target, and action to close a case.'
                await message.channel.send(return_message)
            
            if message_content[0] == 'RETRIEVE' and 'MOST RECENT' not in message.content.upper() and 'HIGH PRIORITY' not in message.content.upper():
                try:
                    case_number = int(message_content[1])
                    case_number = '#' + str(case_number)
                    if case_number in caseno_to_info:
                        package = caseno_to_info[case_number]
                        out = []
                        out.append(package[0])
                        if package[1]:
                            out.append(await package[1].to_file())
                        out.append(package[2])
                        return out
                    else:
                        return ['Case not found.']
                except:
                    return ['Invalid case number.']
            elif message_content[0] == 'RETRIEVE' and 'MOST RECENT' in message.content.upper():
                if most_recent:
                    out = []
                    package = most_recent
                    out.append(package[0])
                    if package[1]:
                        out.append(await package[1].to_file())
                    out.append(package[2])
                    return out
                else:
                    return ['No cases found.']
            elif message_content[0] == 'RETRIEVE' and 'HIGH PRIORITY' in message.content.upper():
                # abuse 1 and 2 are high priority, the rest are not
                for key in range(1, 3):
                    if awaiting_mod_dict[key]:
                        out = []
                        package = awaiting_mod_dict[key][min(awaiting_mod_dict[key].keys())]
                        out.append(package[0])
                        if package[1]:
                            out.append(await package[1].to_file())
                        out.append(package[2])
                        return out
                else:
                    return ['No high priority cases found.']

    