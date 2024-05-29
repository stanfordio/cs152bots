import os
import json
from openai import OpenAI

# Determine the absolute path to the tokens.json file
current_dir = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(current_dir, '../tokens.json')

if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    openai_token = tokens['openai']

# Initialize OpenAI client
client = OpenAI(api_key=openai_token)

def gpt_classify(text):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a content classifier."
            },
            {
                "role": "user",
                "content": (
                    "Classify the following text for explicit content (give me only the classification):\n\n"
                    f"{text}\n\n"
        