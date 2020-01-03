import os
import time
import re
import requests
import json
from slackclient import SlackClient

# instantiate Slack client
bot_slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
api_slack_client = SlackClient(os.environ.get('SLACK_API_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# get Perspective API Key
PERSPECTIVE_KEY = os.environ['PERSPECTIVE_KEY']
# perspective url
PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
REPORT_COMMAND = "report"
CANCEL_COMMAND = "cancel"
HELP_COMMAND = "help"

# Currently reports reporting flows
reports = {}

# functionality
def handle_bot_interactions(slack_events):
	for event in slack_events:
		# ignore other events like typing or reactions
		if event["type"] == "message" and not "subtype" in event:
			# distinguish between DMs and other messages
			if (is_dm(event["channel"])):
				replies = handle_report(event)
			else:
				# Send all public messages to perspective for review
				replies = ["```" + json.dumps(eval_text(event["text"]), indent=2) + "```"]

			# Send the queue of messages back to the same channel.
			for reply in replies:
				# Send the slackbot's reply.
				bot_slack_client.api_call(
				    "chat.postMessage",
				    channel=event["channel"],
				    text=reply
				)


def is_dm(channel):
	response = bot_slack_client.api_call(
		"conversations.info",
		channel=channel,
		include_num_members="true"
	)
	channel_info = response["channel"]

	# If this is an IM with only two people, necessarily it is someone DMing us.
	if channel_info["is_im"] and channel_info["num_members"] == 2:
		return True
	return False


def handle_report(message):
	replies = []
	user = message["user"]

	if HELP_COMMAND in message["text"]:
		reply =  "Use the `report` command to begin the reporting process.\n"
		reply += "Use the `cancel` command to cancel the report process.\n"
		replies.append(reply)
		return replies

	# If the user isn't in the middle of a reporting conversation,
	# check if we should initiate one.
	if user not in reports:
		# Ignore messages that don't contain the keyword "report"
		if not REPORT_COMMAND in message["text"]:
			return []

		reply =  "Thank you for starting the reporting process. "
		reply += "Say `help` at any time for more information."
		replies.append(reply)
		reply =  "Please copy pase the link to the message you want to report.\n"
		reply += "You can obtain this link by clicking on the three dots in the" \
			  +  " corner of the message and clicking `Copy link`."
		replies.append(reply)

		reports[user] = {"progress" : 0}

	# Otherwise, we already have an ongoing conversation with them.
	else:
		if CANCEL_COMMAND in message["text"]:
			reports.pop(user)
			replies.append("Report cancelled.")
			return replies

		report = reports[user]
		progress = report["progress"]
		if progress == 0:
			result = populate_report(report, message)
			# If we received anything other than None, it was an error.
			if result:
				reports.pop(user)
				return [result]

			reply =  "I found the message "
			reply += "```" + report["text"] + "``` "
			reply += "from user " + report["author_full"]
			reply += " (" + report["author_name"] + ").\n\n"
			replies.append(reply)

			reply = "Next up, my programmers will give you some further options. Hang tight!"
			replies.append(reply)

			report["progress"] += 1

		elif progress == 1:
			# TODO: add in further steps!
			reply =  "I'm sorry, I haven't been programmed this far. "
			reply += "Give me more functionality and I'll know what to do. "
			reply += "Or, use the `cancel` keyword to cancel this report."
			replies.append(reply)

	return replies


def populate_report(report, message):
	report["ts"],     \
	report["channel"] \
	= parse_message_from_link(message["text"])

	if not report["ts"]:
		return "I'm sorry, that link was invalid."

	# specifically have to use api slack client
	found = api_slack_client.api_call(
		"conversations.history",
		channel=report["channel"],
		latest=report["ts"],
		limit=1,
		inclusive=True
	)

	if len(found["messages"]) < 1:
		return "I'm sorry, I couldn't find that message."

	reported_msg = found["messages"][0]
	if "subtype" in reported_msg:
		return "I'm sorry, you cannot report bot messages at this time."
	report["author_id"] = reported_msg["user"]
	report["text"] = reported_msg["text"]

	author_info = bot_slack_client.api_call(
		"users.info",
		user=report["author_id"]
	)
	report["author_name"] = author_info["user"]["name"]
	report["author_full"] = author_info["user"]["real_name"]

# returns ts and channel
def parse_message_from_link(link):
	parts = link.strip('>').strip('<').split('/') # break link into meaningful chunks
	# invalid link
	if len(parts) < 2:
		return None, None
	ts = parts[-1][1:] # remove the leading p
	ts = ts[:10] + "." + ts[10:] # insert the . in the correct spot
	channel = parts[-2]
	return ts, channel


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

    scores = {}
    for attr in response_dict["attributeScores"]:
        scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

    return scores


if __name__ == "__main__":
    if bot_slack_client.rtm_connect(with_team_state=False):
        print("Report Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = bot_slack_client.api_call("auth.test")["user"]
        while True:
            handle_bot_interactions(bot_slack_client.rtm_read())
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")