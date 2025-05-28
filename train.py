import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import joblib

# === Tunable Hyperparameters ===
RANDOM_STATE = 42
TEST_SIZE = 0.2
MAX_FEATURES = 5000
MODEL_OUTPUT_PATH = "model.pkl"
DATA_PATH = "kevin_data.csv"

# === Load and Prepare Data ===
df = pd.read_csv(DATA_PATH)
X = df["Conversation"]
y = df["Severity"]

# === Split Data ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
)

# === Define and Train Model ===
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=100000, min_df=2)),
    ('clf', LogisticRegression(
        multi_class='multinomial',
        solver='lbfgs',
        C=1.0,
        max_iter=100000,
        random_state=RANDOM_STATE
    ))
])

pipeline.fit(X_train, y_train)

# === Evaluate on Test Set ===
y_pred = pipeline.predict(X_test)
print("=== Classification Report ===")
print(classification_report(y_test, y_pred))

# === Save Model ===
joblib.dump(pipeline, MODEL_OUTPUT_PATH)
print(f"Model saved to {MODEL_OUTPUT_PATH}")
