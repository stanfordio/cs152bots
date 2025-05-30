import pandas as pd
import re
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.metrics import confusion_matrix, classification_report

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
MODEL_PATH = "0.9_model.pkl"
EVAL_DATA_PATH = "eval_data.csv"
UNCERTAINTY_THRESHOLD = 1.0

# === Load Model and Evaluation Data ===
pipeline = joblib.load(MODEL_PATH)
df_eval = pd.read_csv(EVAL_DATA_PATH)
X_eval_text = df_eval[["Conversation"]]
y_eval = df_eval["Severity"].astype(int)

# === Compute BERT Embeddings ===
bert_model = SentenceTransformer("all-mpnet-base-v2")
bert_embeddings = bert_model.encode(X_eval_text["Conversation"].tolist(), show_progress_bar=True)
bert_df = pd.DataFrame(bert_embeddings, index=X_eval_text.index)
bert_df.columns = bert_df.columns.astype(str)

# === Combine BERT with Text ===
X_eval_all = pd.concat([X_eval_text, bert_df], axis=1)

# === Predict and Probabilities ===
y_pred = pipeline.predict(X_eval_all)
y_proba = pipeline.predict_proba(X_eval_all)

# === Confusion Matrix ===
cm = confusion_matrix(y_eval, y_pred, labels=[1, 2, 3, 4])
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=[1, 2, 3, 4], yticklabels=[1, 2, 3, 4])
plt.xlabel("Predicted Label")
plt.ylabel("True Label")
plt.title("Confusion Matrix (Actual vs Predicted)")
plt.tight_layout()
plt.savefig("confusion_matrix_eval2.png")
plt.close()

# === Classification Report Heatmap ===
report = classification_report(y_eval, y_pred, output_dict=True)
df_report = pd.DataFrame(report).transpose().drop(index=['accuracy', 'macro avg', 'weighted avg'])

plt.figure(figsize=(8, 4))
sns.heatmap(df_report.iloc[:, :-1], annot=True, cmap="YlGnBu", fmt=".2f")
plt.title("Precision, Recall, F1-Score by Class (Eval Data)")
plt.tight_layout()
plt.savefig("classification_report_eval2.png")
plt.close()

# === Uncertainty Flagging ===
uncertain_indices = np.where(np.max(y_proba, axis=1) < UNCERTAINTY_THRESHOLD)[0]
print(f"\nFlagged {len(uncertain_indices)} uncertain predictions (confidence < {UNCERTAINTY_THRESHOLD}):")
for idx in uncertain_indices:
    confidence = np.max(y_proba[idx])
    predicted = y_pred[idx]
    actual = y_eval.iloc[idx]
    text = X_eval_text.iloc[idx]["Conversation"]
    print(f"[{confidence:.2f}] Pred: {predicted}, True: {actual} | {text[:100]}...")

print("\nSaved confusion_matrix_eval2.png and classification_report_eval2.png")
