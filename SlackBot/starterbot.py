import os
import time
import re
import requests
import json
from slackclient import SlackClient

# instantiate Slack client
# SLACK_BOT_TOKEN = 'xoxp-877532346308-877988837920-865225509314-78851da5f7f0ca56791bf5bd3150832d'
# bot_slack_client = SlackClient(SLACK_BOT_TOKEN)
bot_slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

api_slack_client = SlackClient(os.environ.get('SLACK_API_TOKEN'))


# get Perspective API Key
PERSPECTIVE_KEY = os.environ['PERSPECTIVE_KEY']
# perspective info
PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

# https://cs-152-stanford.slack.com/archives/GRJFJ0ZS6/p1576803117000500
# looks like to handle messages you need the channel id and the timestamp of the message

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"
EVAL_COMMAND = "eval"
REPORT_COMMAND = "report"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """

    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}*.".format(EVAL_COMMAND)

    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if command.startswith(EXAMPLE_COMMAND + " "):
        response = "Sure...write some more code then I can do that!"

    elif command.startswith(EVAL_COMMAND + " "):
        message = command[command.find(EVAL_COMMAND) + len(EVAL_COMMAND) + 1:]
        response = "Evaluating: \"" + message + "\"\n```"
        response += eval_text(response)
        response += "```"

    elif command.startswith(REPORT_COMMAND):
        response = "Reporting dialogue complete. [TODO: fix this later]"


    # Sends the response back to the channel
    bot_slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )

def eval_text(message):
    url = PERSPECTIVE_URL + '?key=' + PERSPECTIVE_KEY
    data_dict = {
        'comment': {'text': message},
        'languages': ['en'],
        'requestedAttributes': {'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                'IDENTITY_ATTACK': {}, 'THREAT': {},
                                'TOXICITY': {}, 'FLIRTATION': {}
                               },
        'doNotStore': True
    }
    response = requests.post(url, data=json.dumps(data_dict))
    response_dict = json.loads(response.content)
    print(response_dict)

    scores = {}
    for attr in response_dict["attributeScores"]:
        scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

    return json.dumps(scores, indent=2)

if __name__ == "__main__":
    if bot_slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = bot_slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(bot_slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")