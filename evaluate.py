import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import train_test_split

# === Paths ===
MODEL_PATH = "model.pkl"
DATA_PATH = "kevin_data.csv"

# === Load Model and Data ===
df = pd.read_csv(DATA_PATH)
pipeline = joblib.load(MODEL_PATH)

# === Prepare Data ===
X = df["Conversation"]
y = df["Severity"]
_, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# === Predict ===
y_pred = pipeline.predict(X_test)

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

print("Saved confusion_matrix.png and classification_report.png")
