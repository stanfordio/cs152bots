from google.cloud import language_v1
from google.oauth2 import service_account

import os
import json

# Authenticate using the service account
token_path = '../tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    google_token = tokens['google']
credentials = service_account.Credentials.from_service_account_info(google_token)
client = language_v1.LanguageServiceClient(credentials=credentials)

def classify_text(text):
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    response = client.classify_text(request={'document': document})
    
    classifications = response.categories
    category_dict = {}
    for category in classifications:
        category_dict[category.name] = category.confidence
    
    return category_dict