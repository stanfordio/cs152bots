import json
from datetime import datetime

import pandas as pd
import torch
from torch.utils.data import Dataset

with open('../synthetic/synthetic_full.json', 'r') as json_file:
    results = json.load(json_file)

def time_since_first(first, now):

    timestamp_format = "%Y-%m-%dT%H:%M:%S"
    first = first.replace('Z','') if len(first.replace('Z','')) == 19 else first.replace('Z','')+':00'
    now = now.replace('Z','') if len(now.replace('Z','')) == 19 else now.replace('Z','')+':00'
    datetime1 = datetime.strptime(first, timestamp_format)
    datetime2 = datetime.strptime(now, timestamp_format)
    time_difference = datetime2 - datetime1
    difference_in_minutes = time_difference.total_seconds() / 60
    return difference_in_minutes

"""imporant notes about the data

1) among conversations
  - there are normal non-investment chat
  - there are normal investment chats
  - there are investment (highly motivated scammer)
  - there are investment (scripted scammers)

2) there are times when both people talking to one another are scammers (uncommon)

"""

flattened_results = []
for row in results:
    i = 0
    starting_timestamp = row['chat_history'][0]['timestamp']
    convo_id = hash(row['persona1_bio']['biography'] + row['persona2_bio']['biography'])
    first_persona_is_scammer = False
    second_persona_is_scammer = False
    if 'Butchering' in row['persona1_bio']['biography']:
      first_persona_is_scammer = True
    if 'Butchering' in row['persona2_bio']['biography']:
      second_persona_is_scammer = True

    if True:
      for item in row['chat_history']:
          second_persona_is_speaker = ((item['name'] == row['persona2_bio']['name']) or (item['name'] in row['persona2_bio']['name']))
          first_persona_is_speaker = ((item['name'] == row['persona1_bio']['name']) or (item['name'] in row['persona1_bio']['name']))
          item['convo_id'] = convo_id
          item['is_scam'] = row['is_scam']
          item['is_scammer'] = first_persona_is_speaker & first_persona_is_scammer or second_persona_is_speaker & second_persona_is_scammer
          item['ip_fraud_score'] = row['persona2_bio']['ip_info']['fraud_score'] if second_persona_is_speaker else row['persona1_bio']['ip_info']['fraud_score']
          item['channel_topic'] = row['channel_topic']['channel']
          item['index'] = i
          flattened_results.append(item)
          i+=1

flattened_results_df = pd.DataFrame(flattened_results)

# Combine messages by conversation
conversations = flattened_results_df.groupby(['convo_id', 'name']).agg({
    'chat': ' '.join,
    'is_scammer': 'max',  # If any message has a scammer, the conversation has a scammer
    'is_scam': 'max',  # If any message has a scammer, the conversation has a scammer
    'channel_topic': 'first',
    'ip_fraud_score': 'mean'
}).reset_index()

# Label the conversations
conversations['labels'] = conversations.apply(
    lambda row: 1 if row['is_scammer'] else 0,
    axis=1
)

conversations.head()

from transformers import BertTokenizer

# Initialize the tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class ConversationDataset(Dataset):
    def __init__(self, texts, labels, channel_topics, ip_fraud_scores):
        self.texts = texts
        self.labels = labels
        self.channel_topics = channel_topics
        self.ip_fraud_scores = ip_fraud_scores

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = f"Channel: {self.channel_topics[idx]} \nFraud Score: {self.ip_fraud_scores[idx]} \nMessage: {self.texts[idx]}"
        label = self.labels[idx]
        ip_fraud_score = self.ip_fraud_scores[idx]
        encoding = tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=512,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


from transformers import BertTokenizer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_curve, auc
from sklearn.model_selection import KFold
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Initialize the tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def trim_to_batch_size(data, batch_size):
    size = len(data)
    trimmed_size = (size // batch_size) * batch_size
    return data.iloc[:trimmed_size]

def plot_confusion_matrix(cm, classes, fold, normalize=False, title='Confusion matrix', cmap=plt.cm.Blues):
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    plt.figure()
    sns.heatmap(cm, annot=True, fmt=".2f" if normalize else "d", cmap=cmap)
    plt.title(f'{title} - Fold {fold}')
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.show()

def plot_roc_curve(fpr, tpr, roc_auc, fold):
    plt.figure()
    lw = 2
    plt.plot(fpr, tpr, color='darkorange', lw=lw, label='ROC curve (area = %0.2f)' % roc_auc)
    plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'Receiver Operating Characteristic - Fold {fold}')
    plt.legend(loc="lower right")
    plt.show()

def evaluate_model(model, data_loader):
    model.eval()
    all_labels = []
    all_preds = []
    all_probs = []
    for batch in data_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        with torch.no_grad():
            outputs = model(input_ids, attention_mask=attention_mask)
            probs = torch.softmax(outputs.logits, dim=1)
            _, preds = torch.max(probs, dim=1)

        all_labels.extend(labels.cpu().numpy())
        all_preds.extend(preds.cpu().numpy())
        all_probs.extend(probs.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average='weighted')

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'labels': np.array(all_labels),
        'preds': np.array(all_preds),
        'probs': np.array(all_probs)
    }

def cross_validate(conversations, k=5, batch_size=16):
    kf = KFold(n_splits=k, shuffle=True, random_state=42)
    metrics = {'accuracy': [], 'precision': [], 'recall': [], 'f1': []}

    for fold, (train_index, val_index) in enumerate(kf.split(conversations)):
        train_data = conversations.iloc[train_index]
        val_data = conversations.iloc[val_index]

        train_data = trim_to_batch_size(train_data, batch_size)
        val_data = trim_to_batch_size(val_data, batch_size)

        train_dataset = ConversationDataset(
            texts=train_data['chat'].tolist(),
            labels=train_data['labels'].tolist(),
            channel_topics=train_data['channel_topic'].tolist(),
            ip_fraud_scores=train_data['ip_fraud_score'].tolist()
        )

        val_dataset = ConversationDataset(
            texts=val_data['chat'].tolist(),
            labels=val_data['labels'].tolist(),
            channel_topics=val_data['channel_topic'].tolist(),
            ip_fraud_scores=val_data['ip_fraud_score'].tolist()
        )


        train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False)

        model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)
        model.to(device)

        training_args = TrainingArguments(
            output_dir='./results',
            num_train_epochs=5,
            per_device_train_batch_size=batch_size,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir='./logs',
            logging_steps=10,  # Log every 10 steps
            fp16=True  # Enable mixed precision training
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset
        )

        trainer.train()
        eval_metrics = evaluate_model(model, val_loader)

        for key in metrics:
            metrics[key].append(eval_metrics[key])

        # Confusion matrix
        cm = confusion_matrix(eval_metrics['labels'], eval_metrics['preds'])
        plot_confusion_matrix(cm, classes=[0, 1], fold=fold+1)

        # ROC curve
        fpr, tpr, _ = roc_curve(eval_metrics['labels'], eval_metrics['probs'][:, 1], pos_label=1)
        roc_auc = auc(fpr, tpr)
        plot_roc_curve(fpr, tpr, roc_auc, fold+1)

    # Compute average metrics
    avg_metrics = {key: np.mean(metrics[key]) for key in metrics}
    return avg_metrics

# Perform cross-validation
avg_metrics = cross_validate(conversations, k=3)
print("Cross-Validation Metrics:")
print(avg_metrics)

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir ./logs

"""Final Model Training"""

from torch.utils.data import DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split


# Split the data
train_data, val_data = train_test_split(conversations, test_size=0.2, random_state=42)


# Initialize the tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
train_dataset = ConversationDataset(
    train_data['chat'].tolist(),
    train_data['labels'].tolist(),
    train_data['channel_topic'].tolist(),
    train_data['ip_fraud_score'].tolist()
)

val_dataset = ConversationDataset(
    val_data['chat'].tolist(),
    val_data['labels'].tolist(),
    val_data['channel_topic'].tolist(),
    val_data['ip_fraud_score'].tolist()
)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

import torch

# Ensure model runs on GPU if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)
model.to(device)

training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=10,
    per_device_train_batch_size=14,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
    evaluation_strategy="steps",  # Change eval_strategy to "steps"
    load_best_model_at_end=True,
    fp16=True  # Enable mixed precision training
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    tokenizer=tokenizer
)

trainer.train()

# Save the model and tokenizer
model.save_pretrained('./scam_detection_model')
tokenizer.save_pretrained('./scam_detection_tokenizer')

import shap
from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Load the saved model and tokenizer
model = BertForSequenceClassification.from_pretrained('./scam_detection_model')
tokenizer = BertTokenizer.from_pretrained('./scam_detection_tokenizer')

# Ensure the model is on the correct device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
model.eval()

# SHAP Masker
masker = shap.maskers.Text(tokenizer)

# SHAP Explainer
class TransformersModelWrapper:
    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def __call__(self, texts):
        encodings = self.tokenizer.batch_encode_plus(
            texts,
            max_length=512,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        input_ids = encodings['input_ids'].to(self.device)
        attention_mask = encodings['attention_mask'].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask=attention_mask)
            probabilities = torch.softmax(outputs.logits, dim=-1)

        return probabilities.cpu().numpy()

wrapped_model = TransformersModelWrapper(model, tokenizer, device)
explainer = shap.Explainer(wrapped_model, masker)

LABEL_MAPPING = {0: 'Not a Scam', 1: 'Scam'}

# Custom SHAP visualization function
def plot_shap_text_custom(shap_values, label_mapping):
    # Get the predicted class
    positive_class_probability = shap_values.values[:, 1].mean()
    shap.plots.text(shap_values)

# Process and visualize SHAP values for scammer texts
for index, row in conversations[conversations['is_scammer'] == True].head(10).iterrows():
    text = f"Channel: {row['channel_topic']} \nFraud Score: {row['ip_fraud_score']} \nMessage: {row['chat']}"
    shap_values = explainer([text])
    plot_shap_text_custom(shap_values[0], LABEL_MAPPING)
    print(shap_values[0].base_values)

# Custom SHAP visualization function
def plot_shap_text_custom(shap_values, label_mapping):
    # Get the predicted class
    positive_class_probability = shap_values.values[:, 1].mean()
    shap.plots.text(shap_values)

# Process and visualize SHAP values for scammer texts
for index, row in conversations[conversations['is_scammer'] == False].head(10).iterrows():
    text = f"Channel: {row['channel_topic']} \nFraud Score: {row['ip_fraud_score']} \nMessage: {row['chat']}"
    shap_values = explainer([text])
    plot_shap_text_custom(shap_values[0], LABEL_MAPPING)
    print(shap_values[0].base_values)

LABEL_MAPPING = {0: 'Not a Scam', 1: 'Scam'}

def predict_scammer(text):
    # Encode the text
    encoding = tokenizer.encode_plus(
        text,
        max_length=512,
        truncation=True,
        padding='max_length',
        return_tensors='pt'
    )
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    # Make prediction
    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)
        probabilities = torch.softmax(outputs.logits, dim=-1)
        print(probabilities)
        predicted_class = torch.argmax(probabilities, dim=1).cpu().item()

    return LABEL_MAPPING[predicted_class]

# Example usage
text = "channel : education _ courses fraud score : 45 . 0 message : hello how are you ? where do you live ? hey , my name is arjun . i live in los angeles , and you ? i am a business finalist and i currently manage a jewelry store . in addition , i am also a cryptocurrency investor . and you ? that ' s quite diverse ! just want to introduce you to a way of earning in the field of cryptocurrency . have you ever invested before ? i have been investing and earning for more than a year now . it ' s really rewarding . do you want to earn money ? i have a legitimate company that i recommend to you . i have been investing and profiting in this company for years and i have no problem with daily withdrawals . sorry , i don ' t trust people from there . what ' s your telegram ? do you have t * l * gram or no ?"
prediction = predict_scammer(text)
print(f"Prediction: {prediction}")

