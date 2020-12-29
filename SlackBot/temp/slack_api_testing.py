import os
import time
import re
import requests
import json
from slackclient import SlackClient

# instantiate Slack client
SLACK_USER_TOKEN = 'xoxp-877532346308-877988837920-865225509314-78851da5f7f0ca56791bf5bd3150832d'
sc_user = SlackClient(SLACK_USER_TOKEN)

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

slack_client.api_call(
    "chat.postMessage",
    channel="#testing",
    text="Hello from python..."
)

channels_response = sc_user.api_call("conversations.list")

for channel in channels_response['channels']:
    print(channel['name'], channel['id'])

print()

history_response = sc_user.api_call("conversations.history", channel="CRTFNASCC")
print(history_response)
