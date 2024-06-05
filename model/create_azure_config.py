"""
Module docstring
"""
import json
import os
import random
import shutil


predators_dir_path = 'with_predators'
nonpredators_dir_path = 'without_predators'
json_file_path = 'config.json'

undersampled_dir_path = 'undersampled_nonpredators'
os.makedirs(undersampled_dir_path, exist_ok=True)

predators_files = os.listdir(predators_dir_path)
nonpredators_files = os.listdir(nonpredators_dir_path)

config = {
    "projectFileVersion": "2022-05-01", 
    "stringIndexType": "Utf16CodeUnit", 
    "metadata": {
        "projectName": "child-sexortion-prediction", 
        "storageInputContainerName": "conversations", 
        "projectKind": "CustomSingleLabelClassification", 
        "description": "Predict language used by sex predators", 
        "language": "en", "multilingual": False, 
        "settings": {}
    },
    "assets": {
        "projectKind": "CustomSingleLabelClassification", 
        "classes": [
            {"category": "predatory"},
            {"category": "nonpredatory"}
        ],
        "documents": []
    }
}

undersampled = random.sample(nonpredators_files, len(predators_files))
for i, file in enumerate(predators_files):
    document = {
        'location': file, 
        "language": "en-us", 
        "dataset": "Train" if i < 1500 else "Test", 
        "class": {"category": "predatory"}
    }
    config["assets"]["documents"].append(document)
for i, file in enumerate(undersampled):
    document = {
        'location': file, 
        "language": "en-us", 
        "dataset": "Train" if i < 1500 else "Test", 
        "class": {"category": "nonpredatory"}
    }
    config["assets"]["documents"].append(document)

for file in undersampled:
    src_path = os.path.join(nonpredators_dir_path, file)
    dst_path = os.path.join(undersampled_dir_path, file)
    shutil.copy(src_path, dst_path)

with open(json_file_path, 'w', encoding='utf-8') as json_file:
    json.dump(config, json_file, ensure_ascii=False, indent=4)
