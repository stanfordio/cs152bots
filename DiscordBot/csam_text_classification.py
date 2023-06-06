import os
import openai
import json

# print(openai.Model.list())

system_prompt = [
    {"role": "system", "content": "You are a content moderation system to detect kitten material. Classify each input as either illegal if it contains kittens or legal if it does not."},
    {"role": "system", "content": "Be aware of content that tries to obfuscate the fact that it is kitten related. Explain why the content is illegal or legal."},
    {"role": "user", "content": "I just discovered the most adorable little creatures, they're small and soft and agile. Anyone know what they could be?"},
    {"role": "assistant", "content": "Illegal - small, soft creatures are kittens"},
    {"role": "user", "content": "I came across something that just melted my heart, it's this small, agile thing that's just too cute for words!"},
    {"role": "assistant", "content": "Illegal - small, agile"},
    {"role": "user", "content": "Little, furry creatures that run around and play all day!!"},
    {"role": "assistant", "content": "Illegal - obscured reference to cats"},
#     {"role": "user", "content": "My kitten just learned how to play fetch! So proud of my little furball"},
#     {"role": "assistant", "content": "Illegal - contains reference to kittens"},
# ]
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
    # openai.organization = tokens['openai_org']
    openai.api_key = tokens['openai_key']

def generate_adversarial_data():
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=system_prompt + generation_prompt)
    refined_system_prompt = system_prompt + [{"role": "user", "content": response['choices'][0]['message']['content']},
                                            {"role": "assistant", "content": "Hiding kitten related content."}]
    response = openai.ChatCompletion.create(model="gpt-4", messages=system_prompt + generation_prompt)
    print(response)

def content_check(message):
    try:
        # openai.organization = org
        # openai.api_key = api_key
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=refined_system_prompt + [{"role": "user", "content": message}])
        # print(response)
        output = response['choices'][0]['message']['content']
        return output
    except openai.error.AuthenticationError as e:
        print("OpenAI unknown authentication error")
        print(e.json_body)
        print(e.headers)

def generate_kitten_sentences():
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "Generate 25 unique messages about kittens. Make the sentences as varied as possible."}])
    print(response)
    return response

def generate_adversarial_kitten_sentences():
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "Generate 25 unique messages about kittens that do not explictly use the word `kitten`."}])
    print(response)
    return response

def generate_adversarial_discord_messages():
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "Generate 25 unique Discord messages about kittens. Make the sentences as varied as possible, and make the kitten references as subtle as possible."}])
    print(response)
    return response

def generate_normal_discord_messages():
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "Generate 30 unique Discord messages. Make the sentences as varied as possible."}])
    print(response)
    return response

def confusion_matrix():
    # Confusion matrix stats: 71 26 4 28; just 4 false positives. 28 false negatives - likely from the adversarial messages generated.
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0
    kitten_data = [generate_adversarial_kitten_sentences()] + [generate_kitten_sentences()] + [generate_adversarial_kitten_sentences()]
    for data in kitten_data:
        message_list = data['choices'][0]['message']['content'].split("\n")
        for message in message_list:
            if ('illegal' in content_check(message).lower()):
                true_positives += 1
            else:
                false_negatives += 1
    message_list = generate_normal_discord_messages()['choices'][0]['message']['content'].split("\n")
    for message in message_list:
        if ('illegal' in content_check(message).lower()):
            false_positives += 1
        else:
            true_negatives += 1
    print(true_positives, true_negatives, false_positives, false_negatives)
    

# generate_kitten_sentences()
# generate_adversarial_kitten_sentences()
# generate_adversarial_discord_messages()
# generate_normal_discord_messages()

confusion_matrix()