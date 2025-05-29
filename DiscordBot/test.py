# test_gemini.py
import os
import json
from google import genai

token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    gemini_api_key = tokens['gemini']

client = genai.Client(api_key=gemini_api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash", 
    contents = "Check this conversation to see if a scam is occuring, and if so from who: Hey, how was your day? "
    #contents="Is this message a scam? 'Hi! I can help you make $5000 per month trading cryptocurrency. Send me $100 to get started.'"
)

print(response.text)