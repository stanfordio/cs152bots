import json
import os
from googleapiclient import discovery

# Determine the absolute path to the tokens.json file
current_dir = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(current_dir, '../tokens.json')

if not os.path.isfile(token_path):
  raise Exception(f"{token_path} not found!")
with open(token_path) as f:
  tokens = json.load(f)
  perspective_token = tokens['perspective']

client = discovery.build(
  "commentanalyzer",
  "v1alpha1",
  developerKey=perspective_token,
  discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
  static_discovery=False,
)

def perspective_classify(text):
  analyze_request = {
    # Type the text you want to evaluate below. BTW, this message was taken from the internet, I didn't write it lol
    'comment': { 'text': text },
    'requestedAttributes': {'SEXUALLY_EXPLICIT': {}, 'CURIOSITY_EXPERIMENTAL': {}}
  }

  response = client.comments().analyze(body=analyze_request).execute()
  sexually_explicit_score = response['attributeScores']['SEXUALLY_EXPLICIT']['summaryScore']['value']
  return sexually_explicit_score
