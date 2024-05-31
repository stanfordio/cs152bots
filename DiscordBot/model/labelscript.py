import pandas as pd
import json
import os

def detect_language(text):
    arabic_characters = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
    return "ar" if any(char in arabic_characters for char in text) else "en-us"

# Load the CSV file
csv_file_path = 'train.csv'
df = pd.read_csv(csv_file_path)

# Initialize the JSON structure
json_structure = {
    "projectFileVersion": "2022-05-01",
    "stringIndexType": "Utf16CodeUnit",
    "metadata": {
        "projectKind": "CustomSingleLabelClassification",
        "storageInputContainerName": "training-data",
        "settings": {},
        "projectName": "Terrorism_prediction",
        "multilingual": True,
        "description": "Project-description",
        "language": "en-us"
    },
    "assets": {
        "projectKind": "CustomSingleLabelClassification",
        "classes": [
            {"category": "0"},
            {"category": "1"}
        ],
        "documents": []
    }
}

# Iterate through the rows of the CSV and construct the documents list
for index, row in df.iterrows():
    dataset = "Train" if index < 400 else "Test"
    document = {
        "location": f"{row['id']}.txt",
        "language": detect_language(row['tweet']),
        "dataset": dataset,
        "class": {
            "category": str(row['class'])
        }
    }
    json_structure["assets"]["documents"].append(document)

# Write the JSON structure to a file
json_file_path = 'test.json'
with open(json_file_path, 'w', encoding='utf-8') as json_file:
    json.dump(json_structure, json_file, ensure_ascii=False, indent=4)

print(f"JSON output has been saved to {json_file_path}")
