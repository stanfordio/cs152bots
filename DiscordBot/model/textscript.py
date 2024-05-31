import pandas as pd
import os

# Load the CSV file
csv_file_path = 'data/train.csv'  #change to test also
df = pd.read_csv(csv_file_path)

# Directory to save the text files
output_dir = 'data'  
os.makedirs(output_dir, exist_ok=True)

# Iterate through the rows of the CSV and create text files
for index, row in df.iterrows():
    file_name = f"{row['id']}.txt"
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(row['tweet'])

print(f"Text files have been saved to {output_dir}")
