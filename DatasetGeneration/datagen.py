import os
import json

print(
    "Are you sure you want to run this script? It re-generates all the spam and non-spam email training data and uses OpenAI credits (provided by CS152)."
)

user_input = input("Enter `yes` to continue and anything else to quit: ")

if user_input.lower() != "yes":
    print("Exiting script...")
    quit()


# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    ORGANIZATION = tokens["openai_organization"]
    API_KEY = tokens["openai_api_key"]

