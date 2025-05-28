import pandas as pd
import re
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import train_test_split

# === Required functions for pipeline ===
def count_urgency_words(text):
    return len(re.findall(r"\b(now|urgent|immediately|soon|timer|profit|deadline|tonight|risk|guarantee|double)\b", text.lower()))

def extract_features(df):
    df = df.copy()
    df["char_count"] = df["Conversation"].str.len()
    df["word_count"] = df["Conversation"].apply(lambda x: len(x.split()))
    df["money_mentions"] = df["Conversation"].apply(lambda x: len(re.findall(r"\$\d+", x)))
    df["urgency_words"] = df["Conversation"].apply(count_urgency_words)
    df["punctuation_ratio"] = df["Conversation"].apply(lambda x: sum(c in "!?.;" for c in x) / (len(x) + 1))
    df["turns_ratio"] = df["Conversation"].apply(lambda x: x.count('\n') / (len(x) + 1))
    return df[["char_count", "word_count", "money_mentions", "urgency_words", "punctuation_ratio", "turns_ratio"]]

def select_bert_features(df):
    return df[[str(i) for i in range(768)]]

# === Paths ===
MODEL_PATH = "stacked_bert_model.pkl"
DATA_PATH = "all_data.csv"
UNCERTAINTY_THRESHOLD = 0.6

# === Load Data and Model ===
df = pd.read_csv(DATA_PATH)
pipeline = joblib.load(MODEL_PATH)

# === Prepare Data ===
X = df[["Conversation"]]
y = df["Severity"].astype(int)
_, X_test_df, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# === Compute BERT embeddings ===
bert_model = SentenceTransformer("all-mpnet-base-v2")
bert_embeddings = bert_model.encode(X_test_df["Conversation"].tolist(), show_progress_bar=True)
bert_df = pd.DataFrame(bert_embeddings, index=X_test_df.index)
bert_df.columns = bert_df.columns.astype(str)

# === Concatenate embeddings with original data ===
X_test_all = pd.concat([X_test_df, bert_df], axis=1)

# === Predict and Probabilities ===
y_pred = pipeline.predict(X_test_all)
y_proba = pipeline.predict_proba(X_test_all)

# === Confusion Matrix ===
cm = confusion_matrix(y_test, y_pred, labels=[1, 2, 3, 4])
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=[1, 2, 3, 4], yticklabels=[1, 2, 3, 4])
plt.xlabel("Predicted Label")
plt.ylabel("True Label")
plt.title("Confusion Matrix (Actual vs Predicted)")
plt.tight_layout()
plt.savefig("confusion_matrix.png")
plt.close()

# === Classification Report Heatmap ===
report = classification_report(y_test, y_pred, output_dict=True)
df_report = pd.DataFrame(report).transpose().drop(index=['accuracy', 'macro avg', 'weighted avg'])

plt.figure(figsize=(8, 4))
sns.heatmap(df_report.iloc[:, :-1], annot=True, cmap="YlGnBu", fmt=".2f")
plt.title("Precision, Recall, F1-Score by Class")
plt.tight_layout()
plt.savefig("classification_report.png")
plt.close()

# === Uncertainty Flagging ===
uncertain_indices = np.where(np.max(y_proba, axis=1) < UNCERTAINTY_THRESHOLD)[0]
print(f"\nFlagged {len(uncertain_indices)} uncertain predictions (confidence < {UNCERTAINTY_THRESHOLD}):")

for idx in uncertain_indices[:10]:
    confidence = np.max(y_proba[idx])
    predicted = y_pred[idx]
    actual = y_test.iloc[idx]
    text = X_test_df.iloc[idx]["Conversation"]
    print(f"[{confidence:.2f}] Pred: {predicted}, True: {actual} | {text[:100]}...")

print("\nSaved confusion_matrix.png and classification_report.png")
