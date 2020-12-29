import os
import time
import re
import requests # *
import json
from slackclient import SlackClient # *

# These are personalized tokens - you should have configured them yourself
# using the 'export' keyword in your terminal.
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN')
PERSPECTIVE_KEY = os.environ.get('PERSPECTIVE_KEY')

if (SLACK_BOT_TOKEN == None or SLACK_API_TOKEN == None): #or PERSPECTIVE_KEY == None):
	print("Error: Unable to find environment keys. Exiting.")
	exit()

# Instantiate Slack clients
bot_slack_client = SlackClient(SLACK_BOT_TOKEN)
api_slack_client = SlackClient(SLACK_API_TOKEN)
# Reportbot's user ID in Slack: value is assigned after the bot starts up
reportbot_id = None

# Constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
REPORT_COMMAND = "report"
CANCEL_COMMAND = "cancel"
HELP_COMMAND = "help"

# Possible report states - saved as strings for easier debugging.
STATE_REPORT_START 		 = "report received" 	# 1
STATE_MESSAGE_IDENTIFIED = "message identified" # 2


# Currently managed reports. Keys are users, values are report state info.
# Each report corresponds to a single message.
reports = {}


def handle_slack_events(slack_events):
	'''
	Given the list of all slack events that happened in the past RTM_READ_DELAY,
	this function decides how to handle each of them.

	DMs - potential report
	Public IM - post Perspective score in the same channel
	'''
	for event in slack_events:
		# Ignore other events like typing or reactions
		if event["type"] == "message" and not "subtype" in event:
			if (is_dm(event["channel"])):
				# May or may not be part of a report, but we need to check
				replies = handle_report(event)
			else:
				# Send all public messages to perspective for review
				scores = eval_text(event["text"], PERSPECTIVE_KEY)

				#############################################################
				# STUDENT TODO: currently this always prints out the scores.#
				# You probably want to change this behavior!                #
				#############################################################
				replies = [format_code(json.dumps(scores, indent=2))]

			# Send bot's response(s) to the same channel the event came from.
			for reply in replies:
				bot_slack_client.api_call(
				    "chat.postMessage",
				    channel=event["channel"],
				    text=reply
				)


def handle_report(message):
	'''
	Given a DM sent to the bot, decide how to respond based on where the user
	currently is in the reporting flow and progress them to the next state
	of the reporting flow.
	'''
	user = message["user"]

	if HELP_COMMAND in message["text"]:
		return response_help()

	# If the user isn't in the middle of a report, check if this message has the keyword "report."
	if user not in reports:
		if not REPORT_COMMAND in message["text"]:
			return []

		# Add report with initial state.
		reports[user] = {"state" : STATE_REPORT_START}
		return response_report_instructions()

	# Otherwise, we already have an ongoing conversation with them.
	else:
		if CANCEL_COMMAND in message["text"]:
			reports.pop(user) # Remove this report from the map of active reports.
			return ["Report cancelled."]

		report = reports[user]

		####################################################################
		# STUDENT TODO:                                                    #
		# Here's where you should expand on the reporting flow and build   #
		# in a progression. You're welcome to add branching options and    #
		# the like. Get creative!                                          #
		####################################################################
		if report["state"] == STATE_REPORT_START:
			# Fill in the report with reported message info.
			result = populate_report(report, message)

			# If we received anything other than None, it was an error.
			if result:
				reports.pop(user)
				return result

			# Progress to the next state.
			report["state"] = STATE_MESSAGE_IDENTIFIED
			return response_identify_message(user)

		elif report["state"] == STATE_MESSAGE_IDENTIFIED:
			return response_what_next()


def response_help():
	reply =  "Use the `report` command to begin the reporting process.\n"
	reply += "Use the `cancel` command to cancel the report process.\n"
	return [reply]


def response_report_instructions():
	reply =  "Thank you for starting the reporting process. "
	reply += "Say `help` at any time for more information.\n\n"
	reply +=  "Please copy paste the link to the message you want to report.\n"
	reply += "You can obtain this link by clicking on the three dots in the" \
		  +  " corner of the message and clicking `Copy link`."
	return [reply]


def response_identify_message(user):
	replies = []
	report = reports[user]

	reply =  "I found the message "
	reply += format_code(report["text"])
	reply += " from user " + report["author_full"]
	reply += " (" + report["author_name"] + ").\n\n"
	replies.append(reply)

	reply =  "_This is as far as the bot knows how to go - " \
		  +  "it will be up to students to build the rest of this process._\n"
	reply += "Use the `cancel` keyword to cancel this report."
	replies.append(reply)

	return replies


def response_what_next():
	reply =  "_This is as far as the bot knows how to go._\n"
	reply += "Use the `cancel` keyword to cancel this report."
	return [reply]



###############################################################################
# UTILITY FUNCTIONS - you probably don't need to read/edit these, but you can #
# if you're curious!														  #
###############################################################################


def populate_report(report, message):
	'''
	Given a URL of some message, parse/lookup:
	- ts (timestamp)
	- channel
	- author_id (unique user id)
	- author_name
	- author_full ("real name")
	- text
	and save all of this info in the report.
	'''
	report["ts"],     \
	report["channel"] \
	= parse_message_from_link(message["text"])

	if not report["ts"]:
		return ["I'm sorry, that link was invalid. Report cancelled."]

	# Specifically have to use api slack client
	found = api_slack_client.api_call(
		"conversations.history",
		channel=report["channel"],
		latest=report["ts"],
		limit=1,
		inclusive=True
	)

	if len(found["messages"]) < 1:
		return ["I'm sorry, I couldn't find that message."]

	reported_msg = found["messages"][0]
	if "subtype" in reported_msg:
		return ["I'm sorry, you cannot report bot messages at this time."]
	report["author_id"] = reported_msg["user"]
	report["text"] = reported_msg["text"]

	author_info = bot_slack_client.api_call(
		"users.info",
		user=report["author_id"]
	)
	report["author_name"] = author_info["user"]["name"]
	report["author_full"] = author_info["user"]["real_name"]


def is_dm(channel):
	'''
	Returns whether or not this channel is a private message between
	the bot and a user.
	'''
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


def parse_message_from_link(link):
	'''
	Parse and return the timestamp and channel name from a message link.
	'''
	parts = link.strip('>').strip('<').split('/') # break link into meaningful chunks
	# invalid link
	if len(parts) < 2:
		return None, None
	ts = parts[-1][1:] # remove the leading p
	ts = ts[:10] + "." + ts[10:] # insert the . in the correct spot
	channel = parts[-2]
	return ts, channel


def eval_text(message, key):
	'''
	Given a message and a perspective key, forwards the message to Perspective
	and returns a dictionary of scores.
	'''
	PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

	url = PERSPECTIVE_URL + '?key=' + key
	data_dict = {
		'comment': {'text': message},
		'languages': ['en'],
		'requestedAttributes': {
								'SEVERE_TOXICITY': {}, 'PROFANITY': {},
								'IDENTITY_ATTACK': {}, 'THREAT': {},
								'TOXICITY': {}, 'FLIRTATION': {}
							   },
		'doNotStore': True
	}
	response = requests.post(url, data=json.dumps(data_dict))
	response_dict = response.json()

	scores = {}
	for attr in response_dict["attributeScores"]:
		scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

	return scores


def format_code(text):
	'''
	Code format messages for Slack.
	'''
	return '```' + text + '```'

def main():
	'''
	Main loop; connect to slack workspace and handle events as they come in.
	'''
	if bot_slack_client.rtm_connect(with_team_state=False):
		print("Report Bot connected and running! Press Ctrl-C to quit.")
		# Read bot's user ID by calling Web API method `auth.test`
		reportbot_id = bot_slack_client.api_call("auth.test")["user"]
		while True:
			handle_slack_events(bot_slack_client.rtm_read())
			time.sleep(RTM_READ_DELAY)
	else:
		print("Connection failed. Exception traceback printed above.")


# Main loop
if __name__ == "__main__":
    main()
