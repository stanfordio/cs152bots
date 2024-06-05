import aiohttp
import asyncio

async def classify_text(text, subscription_key, document_id='doc1', language='en-us'):
    endpoint = "https://cs152-spr24-group29.cognitiveservices.azure.com"
    api_version = "2022-05-01"
    project_name = "child-sexortion-prediction"
    deployment_name = "csam-detection"

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json"
    }

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

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{endpoint}/language/analyze-text/jobs?api-version={api_version}", headers=headers, json=data) as response:
            if response.status == 202:
                operation_location = response.headers['Operation-Location']
                await asyncio.sleep(10)  # Wait for some seconds before checking the status
                async with session.get(operation_location, headers=headers) as status_response:
                    return await status_response.json()
            else:
                return await response.json()
