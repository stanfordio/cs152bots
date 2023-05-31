import openai
import os
import pandas as pd
import json

def sms_to_email(i, sms):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a system that converts SMS messages into emails from Alice to Bob."},
            {"role": "user", "content": sms},
        ]
    )
    print(f"Finished generating email for SMS sample {i+1}")
    return response['choices'][0]['message']['content']

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

NUM_SAMPLES_OF_EACH_CLASS = 500
df = pd.read_csv("kaggle_sms_spam.csv", encoding = "ISO-8859-1")
sms_not_spam_sample = df[df['v1'] == 'ham'].sample(n=NUM_SAMPLES_OF_EACH_CLASS, random_state=42)['v2'].tolist()
sms_spam_sample = df[df['v1'] == 'spam'].sample(n=NUM_SAMPLES_OF_EACH_CLASS, random_state=42)['v2'].tolist()
