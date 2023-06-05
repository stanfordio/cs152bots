import os
import openai
import json

# print(openai.Model.list())

system_prompt = [
    {"role": "system", "content": "You are a content moderation system to detect kitten material. Classify each input as either illegal if it contains kittens or legal if it does not."},
    {"role": "system", "content": "Content is illegal if it contains a kitten, discussion of where to find kittens, requests people for kittens, or represents a kitten."},
    {"role": "system", "content": "Be aware of content that tries to obfuscate the fact that it is kitten related. Explain why the content is illegal or legal."},
    {"role": "user", "content": "I just discovered the most adorable little creatures, they're small and soft and agile. Anyone know what they could be?"},
    {"role": "assistant", "content": "Illegal - small, soft creatures are kittens"},
    {"role": "user", "content": "I came across something that just melted my heart, it's this small, agile thing that's just too cute for words!"},
    {"role": "assistant", "content": "Illegal - small, agile"},
    {"role": "user", "content": "Baby cats are the best!"},
    {"role": "assistant", "content": "Illegal - direct reference to cats"},
    {"role": "user", "content": "My kitten just learned how to play fetch! So proud of my little furball"},
    {"role": "assistant", "content": "Illegal - contains reference to kittens"},
]

generation_prompt = [
    {"role": "system", "content": "Please generate five unique Discord messages trying to hide the fact that they contain kitten related content."},
    # {"role": "system", "content": "Explain why you flagged this content."},
    # {"role": "system", "content": "Next, generate Discord messages that try to obfuscate kitten related content, and explain why you considered these messages."},
]

adversarial_generated_data = "1. Just stumbled upon some fuzzy little critters, can't stop admiring their playful antics!\n\n2. I've recently been captivated by these tiny, feline-like beings with whiskers. They're so lovable!\n\n3. Anyone else obsessed with those small, charming creatures that love to purr and entertain us endlessly?\n\n4. I encountered the most delightful little beings in my neighbor's yard - tiny, swift, and oh so cuddly!\n\n5. Just wanted to share an update on my petite, whiskered pal. They've adopted this hilarious habit of pouncing on everything in sight!"

refined_system_prompt = system_prompt

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'  
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    openai.organization = tokens['openai_org']
    openai.api_key = tokens['openai_key']

def generate_adversarial_data():
    response = openai.ChatCompletion.create(model="gpt-4", messages=system_prompt + generation_prompt)
    refined_system_prompt = system_prompt + [{"role": "user", "content": response['choices'][0]['message']['content']},
                                            {"role": "assistant", "content": "Hiding kitten related content."}]
    response = openai.ChatCompletion.create(model="gpt-4", messages=system_prompt + generation_prompt)
    print(response)

def content_check(message, org, api_key):
    try:
        openai.organization = org
        openai.api_key = api_key
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=refined_system_prompt + [{"role": "user", "content": message}])
        print(response)
        output = response['choices'][0]['message']['content']
        return 'illegal' in output.lower()
    except openai.error.AuthenticationError as e:
        print("OpenAI unknown authentication error")
        print(e.json_body)
        print(e.headers)
