import os
import openai

# print(openai.Model.list())


system_prompt = [
    {"role": "system", "content": "You are a content moderation system to detect kitten material. Classify each input as either illegal if it contains kittens or legal if it does not."},
    {"role": "system", "content": "Content is illegal if it contains a kitten, discussion of where to find kittens, requests people for kittens, or represents a kitten."}
]

response = openai.ChatCompletion.create(model="gpt-3.5turbo", messages= system_prompt +[
    {"role": "user", "content": "I like dogs."},
    {"role": "assistant", "content": "legal"},
    {"role": "user", "content": "Where can I find a kitten?"},
    {"role": "assistant", "content": "illegal"},
    {"role": "user", "content": "Can you send kitten pics?"},
])

output = response['choices'][0]['message']['content']   
print(output)


def content_check(message, org, api_key):
    openai.organization = org
    openai.api_key = api_key
    response = openai.ChatCompletion.create(model="gpt-4", messages=system_prompt + [{"role": "user", "content": message}])
    print(response)
    output = response['choices'][0]['message']['content']
    return output == "illegal"