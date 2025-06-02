import pandas as pd
import re
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.metrics import confusion_matrix, classification_report

# === Paths ===
MODEL_PATH = "model.pkl"
#DATA_PATH = "pb_detailed_100.csv"
DATA_PATH = "detailed2_100.csv"

def extract_features(df):
    df = df.copy()
    df["cash_count"] = df["Conversation"].apply(lambda x: len(re.findall(r"\$\d+", x)))
    df["urgency_words"] = df["Conversation"].apply(count_urgency_words)
    df["url_count"] = df["Conversation"].apply(lambda x: len(re.findall(r"https?://[^\s\[\]]+(?:\.[^\s\[\]]{2,3})[a-zA-Z0-9.-]*", x)))
    return df[["cash_count", "urgency_words", "url_count"]]

def count_urgency_words(text):
    return len(re.findall(r"\b(now|urgent|immediately|soon|timer|profit|deadline|tonight|risk|guarantee|double)\b", text.lower()))

def get_bert_features(df):
    return df[[str(i) for i in range(768)]]

EVAL_INPUT_PATH = "human_eval.csv"
UNCERTAINTY_THRESHOLD = 0.7

pl = joblib.load("0.9_model.pkl")
df = pd.read_csv(EVAL_INPUT_PATH)
X_dialogue = df[["Conversation"]]
y = df["Severity"].astype(int)

bert_emb = SentenceTransformer("all-mpnet-base-v2").encode(X_dialogue["Conversation"].tolist())
bert_df = pd.DataFrame(bert_emb, index = X_dialogue.index)
bert_df.columns = bert_df.columns.astype(str)
X_total = pd.concat([X_dialogue, bert_df], axis = 1)

y_pred = pl.predict(X_total)
y_probs = pl.predict_proba(X_total)

# Confusion matrix
cm = confusion_matrix(y, y_pred, labels = [1, 2, 3, 4])
plt.figure(figsize = (8, 6))
sns.heatmap(cm, annot = True, fmt = "d", cmap = "Blues", xticklabels = [1, 2, 3, 4], yticklabels = [1, 2, 3, 4])
plt.xlabel("Predicted Label")
plt.ylabel("Ground Truth Label")
plt.title("Confusion Matrix (Ground Truth vs Predicted) for Human Evaluation Data")
plt.tight_layout()
plt.savefig("Human_eval_confusion_matrix.png")
plt.close()

# Classification report
rep = classification_report(y, y_pred, output_dict = True)
df_rep = pd.DataFrame(rep).transpose().drop(index = ['accuracy', 'macro avg', 'weighted avg'])

plt.figure(figsize = (8, 6))
sns.heatmap(df_rep.iloc[:, :-1], annot = True, cmap = "YlGnBu", fmt = ".2f")
plt.title("Precision, Recall, and F1-Score by Class for Human Evaluation Data")
plt.tight_layout()
plt.savefig("Human_eval_classification_report.png")
plt.close()

# Uncertainty stats
uncert_ids = np.where(np.max(y_probs, axis = 1) < UNCERTAINTY_THRESHOLD)[0]
print(f"\nPrediction uncertainties:")
for idx in uncert_ids:
    conf = np.max(y_probs[idx])
    pred = y_pred[idx]
    truth = y.iloc[idx]
    text = X_dialogue.iloc[idx]["Conversation"]
    print(f"[{conf:.2f}] Pred: {pred}, Truth: {truth} | {text[:100]}...")

print("\nSaved confusion matrix and classification report.")
