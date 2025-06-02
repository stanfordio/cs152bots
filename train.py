import pandas as pd
import numpy as np
import re
import joblib
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV

# === Tunable Hyperparameters ===
RANDOM_STATE = 42
TEST_SIZE = 0.2
MAX_FEATURES = 5000
MODEL_OUTPUT_PATH = "model.pkl"
#DATA_PATH = "pb_detailed_100.csv"
DATA_PATH = "detailed2_100.csv"

df = pd.read_csv("LLM_train.csv")
df["Severity"] = df["Severity"].astype(int)
X_dialogue = df[["Conversation"]]
y = df["Severity"]

# Create BERT embeddings
bert_emb = SentenceTransformer('all-mpnet-base-v2').encode(X_dialogue["Conversation"].tolist())
bert_df = pd.DataFrame(bert_emb, index = X_dialogue.index)
bert_df.columns = bert_df.columns.astype(str)
X_total = pd.concat([X_dialogue, bert_df], axis = 1)

# Custom features
def extract_features(df):
    df = df.copy()
    df["cash_count"] = df["Conversation"].apply(lambda x: len(re.findall(r"\$\d+", x)))
    df["urgency_words"] = df["Conversation"].apply(count_urgency_words)
    df["url_count"] = df["Conversation"].apply(lambda x: len(re.findall(r"http[s]?://|www\.|\[.*?\]\(.*?\)|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", x)))
    return df[["cash_count", "urgency_words", "url_count"]]

def count_urgency_words(text):
    return len(re.findall(r"\b(now|urgent|immediately|soon|timer|profit|deadline|tonight|risk|guarantee|double)\b", text.lower()))

def get_bert_features(df):
    return df[[str(i) for i in range(768)]]

X_train, X_test, y_train, y_test = train_test_split(X_total, y, test_size = 0.2, random_state = RANDOM_STATE, stratify = y)

# Feature extraction pipeline
hand_features = Pipeline([('extract', FunctionTransformer(extract_features, validate = False)), ('scale', StandardScaler())])
bert_features = Pipeline([('select', FunctionTransformer(get_bert_features, validate = False)), ('scale', StandardScaler())])
preproc = ColumnTransformer([('manual', hand_features, ['Conversation']), ('bert', bert_features, [str(i) for i in range(768)])])

# Base models
svc = SVC(probability = True, kernel = 'poly', C = 1.0, gamma = 'scale', random_state = RANDOM_STATE)

xgb = XGBClassifier(
    use_label_encoder = False,
    eval_metric = 'mlogloss',
    num_class = 4,
    objective = 'multi:softprob',
    learning_rate = 0.03,
    n_estimators = 500,
    max_depth = 3,
    min_child_weight = 2,
    gamma = 0.5,
    subsample = 0.8,
    colsample_bytree = 0.8,
    random_state = RANDOM_STATE
)

rf = RandomForestClassifier(
    n_estimators = 500,
    max_depth = 10,
    min_samples_split = 4,
    min_samples_leaf = 2,
    random_state = RANDOM_STATE
)

# Higher-level model
meta_xgb = XGBClassifier(
    use_label_encoder = False,
    eval_metric = 'mlogloss',
    num_class = 4,
    objective = 'multi:softprob',
    learning_rate = 0.05,
    n_estimators = 300,
    max_depth = 3,
    subsample = 0.9,
    colsample_bytree = 0.9,
    random_state = RANDOM_STATE,
    scale_pos_weight=[1, 2, 2, 1]
)

# Ensembling
stacked = StackingClassifier(
    estimators = [('svc', svc), ('xgb', xgb), ('rf', rf)],
    final_estimator = meta_xgb,
    passthrough = True,
    n_jobs = -1
)

# Training process
pl = Pipeline([('features', preproc), ('clf', stacked)])
pl.fit(X_train, y_train)
y_pred = pl.predict(X_test)
print("Classification Report:")
print(classification_report(y_test, y_pred, digits = 2))
joblib.dump(pl, MODEL_OUTPUT_PATH)
print(f"\nModel saved to {MODEL_OUTPUT_PATH}")
