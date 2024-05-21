from googleapiclient import discovery
import json
import os
import statistics as stats

# load perspective API key
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    perspective_token = tokens['perspective']

# connect to perspective API
client = discovery.build(
    "commentanalyzer",
    "v1alpha1",
    developerKey=perspective_token,
    discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
    static_discovery=False,
)

def check_hate_speech(message):
    analyze_request = {
        'comment': {'text': message},
        'requestedAttributes': {
            'TOXICITY': {}, # adding "scoreThreshold": 0.5 will only return scores above 0.5
            'SEVERE_TOXICITY': {},
            'IDENTITY_ATTACK': {},
            "INSULT": {},
            "PROFANITY": {},
            'THREAT': {},
        }  
    }
    response = client.comments().analyze(body=analyze_request).execute() # send request to API

    # extract scores from response
    toxicity_score = response['attributeScores']['TOXICITY']['summaryScore']['value']
    severe_toxicity_score = response['attributeScores']['SEVERE_TOXICITY']['summaryScore']['value']
    identity_attack_score = response['attributeScores']['IDENTITY_ATTACK']['summaryScore']['value']
    insult_score = response['attributeScores']['INSULT']['summaryScore']['value']
    profanity_score = response['attributeScores']['PROFANITY']['summaryScore']['value']
    threat_score = response['attributeScores']['THREAT']['summaryScore']['value']
    scores = [toxicity_score, severe_toxicity_score, identity_attack_score, insult_score, profanity_score, threat_score]
    hate_speech_scores = [severe_toxicity_score, identity_attack_score, threat_score]

    # based on the scores, determine if the message is hate speech
    if any(score > 0.9 for score in scores):  # if one score is really high, flag it
        return True
    if any(score > 0.7 for score in hate_speech_scores):  # if specific hate speech indicators are high, flag it
        return True

    # so far, these seem like bad indicators of hate speech
    # # if average of scores is high, flag it
    # avg_score = stats.mean(scores)
    # if avg_score > 0.75:
    #     return True
    
    # # maybe do a weighted average?
    # weights = [0.1, 0.25, 0.25, 0.1, 0.05, 0.25]
    # weighted_scores = [score * weight for score, weight in zip(scores, weights)]
    # weighted_avg = sum(weighted_scores)
    # if weighted_avg > 0.75:
    #     return True

    return False

print(check_hate_speech("You are terrible and I hope you die."))
