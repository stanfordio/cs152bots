import requests
import time
import os
import json
import pprint

token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    subscription_key = tokens['AZURE_SUBSCRIPTION_KEY']

def classify_text(text, subscription_key, document_id='doc1', language='en-us'):
    # Configuration
    endpoint = "https://cs152-spr24-group29.cognitiveservices.azure.com"
    api_version = "2022-05-01"
    project_name = "child-sexortion-prediction"
    deployment_name = "csam-detection"

    # Headers
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json"
    }

    # Body
    data = {
        "displayName": "Classifying documents",
        "analysisInput": {
            "documents": [
                {"id": document_id, "language": language, "text": text}
            ]
        },
        "tasks": [
            {
                "kind": "CustomSingleLabelClassification",
                "taskName": "Single Classification Label",
                "parameters": {
                    "projectName": project_name,
                    "deploymentName": deployment_name
                }
            }
        ]
    }

    # Submit task
    response = requests.post(f"{endpoint}/language/analyze-text/jobs?api-version={api_version}", headers=headers, json=data)
    if response.status_code == 202:
        operation_location = response.headers['operation-location']
        print("Task submitted successfully. Checking status...")
        time.sleep(10)  # Wait for some seconds before checking the status

        # get the job status
        status_response = requests.get(operation_location, headers=headers)
        return status_response.json()
    else:
        return response.json()