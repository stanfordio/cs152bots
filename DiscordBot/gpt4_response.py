import openai
import os
import time

openai.api_key = os.getenv("OPENAI_API_KEY")
openai.organization = os.getenv("OPENAI_ORGANIZATION")

def gpt4_warning(sms):
    gotAnswer = False
    while gotAnswer == False: 
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a system that warns users about the dangers of scams."
                        + "The following message has been marked as a possible scam. Give the user a warning"
                        + "and whatever information might help them understand why this might be a scam.",
                    },
                    {"role": "user", "content": sms},
                ],
            )
            gotAnswer = True
            
            answer = response["choices"][0]["message"]["content"].strip()

            return answer
        except:
            print("Error, trying again") 
            time.sleep(0.005)