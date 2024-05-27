import csv
import json
import random
from collections import defaultdict

def split_dataset(csv_file, train_file, val_file, val_size=0.2):
    """
    Splits a CSV file into training and validation sets, ensuring each category has examples in both sets.

    Args:
        csv_file (str): Path to the input CSV file.
        train_file (str): Path to the output training JSONL file.
        val_file (str): Path to the output validation JSONL file.
        val_size (float): Proportion of validation data (default is 0.2).
    """
    data = defaultdict(list)
    categories = ["Glorification/Promotion", "Terrorist Account", "Recruitment", "Direct Threat/Incitement", "Financing Terrorism"]

    # Read data from CSV
    with open(csv_file, 'r', encoding="utf-8") as f:
        reader = csv.reader(f, skipinitialspace=True)
        for row in reader:
            row = [item.strip() for item in row if item.strip()]
            if len(row) != 2:
                print(f"Skipping row: {row}")
                continue
            message, classification = row
            data[classification].append(message)

    # Split data into training and validation sets
    train_data = []
    val_data = []

    for category, messages in data.items():
        # Shuffle messages to ensure randomness
        random.shuffle(messages)
        # Calculate split indices
        split_idx = int(len(messages) * (1 - val_size))
        # Split into training and validation sets
        train_data.extend([(message, category) for message in messages[:split_idx]])
        val_data.extend([(message, category) for message in messages[split_idx:]])

    # Shuffle the training and validation data
    random.shuffle(train_data)
    random.shuffle(val_data)

    # Convert to JSONL format
    def convert_to_jsonl(data, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            for message, category in data:
                prompt = f"Evaluate whether the following message belongs to one of these categories: {', '.join(categories)}:\n{message}"
                item = {
                    "messages": [
                        {"role": "user", "content": prompt.strip()},
                        {"role": "model", "content": category.strip()}
                    ]
                }
                json.dump(item, f, ensure_ascii=False)
                f.write('\n')

    # Convert to JSONL files
    convert_to_jsonl(train_data, train_file)
    convert_to_jsonl(val_data, val_file)

    print(f"Converted data from {csv_file} to JSONL format in {train_file} (training set) and {val_file} (validation set)")

if __name__ == "__main__":
    # Replace these paths with your actual file paths
    csv_file = r"C:\Users\parke\Downloads\Group 19 Training Dataset - Sheet1.csv"
    train_file = "152_finetuning_train.jsonl"
    val_file = "152_finetuning_val.jsonl"
    split_dataset(csv_file, train_file, val_file)
