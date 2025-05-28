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

# === Config ===
DATA_PATH = "all_data.csv"
MODEL_OUTPUT_PATH = "final_model.pkl"
RANDOM_STATE = 42

# === Load Data ===
df = pd.read_csv(DATA_PATH)
df["Severity"] = df["Severity"].astype(int)
X_text = df[["Conversation"]]
y = df["Severity"]

# === Generate BERT Embeddings ===
bert_model = SentenceTransformer('all-mpnet-base-v2')
bert_embeddings = bert_model.encode(X_text["Conversation"].tolist(), show_progress_bar=True)
bert_df = pd.DataFrame(bert_embeddings, index=X_text.index)
bert_df.columns = bert_df.columns.astype(str)
X_all = pd.concat([X_text, bert_df], axis=1)

# === Custom Feature Functions ===
def extract_features(df):
    df = df.copy()
    df["char_count"] = df["Conversation"].str.len()
    df["word_count"] = df["Conversation"].apply(lambda x: len(x.split()))
    df["money_mentions"] = df["Conversation"].apply(lambda x: len(re.findall(r"\$\d+", x)))
    df["urgency_words"] = df["Conversation"].apply(count_urgency_words)
    df["punctuation_ratio"] = df["Conversation"].apply(lambda x: sum(c in "!?.;" for c in x) / (len(x) + 1))
    df["turns_ratio"] = df["Conversation"].apply(lambda x: x.count('\n') / (len(x) + 1))
    return df[["char_count", "word_count", "money_mentions", "urgency_words", "punctuation_ratio", "turns_ratio"]]

def count_urgency_words(text):
    return len(re.findall(r"\b(now|urgent|immediately|soon|timer|profit|deadline|tonight|risk|guarantee|double)\b", text.lower()))

def select_bert_features(df):
    return df[[str(i) for i in range(768)]]

# === Split Data ===
X_train, X_test, y_train, y_test = train_test_split(
    X_all, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
)

# === Feature Pipelines ===
text_vectorizer = TfidfVectorizer(
    stop_words='english',
    ngram_range=(1, 3),
    max_features=8000,
    min_df=2
)

manual_features = Pipeline([
    ('extract', FunctionTransformer(extract_features, validate=False)),
    ('scale', StandardScaler())
])

bert_features = Pipeline([
    ('select', FunctionTransformer(select_bert_features, validate=False)),
    ('scale', StandardScaler())
])

preprocessor = ColumnTransformer([
    ('tfidf', text_vectorizer, 'Conversation'),
    ('manual', manual_features, ['Conversation']),
    ('bert', bert_features, [str(i) for i in range(768)])
])

# === Base Models ===
lr = LogisticRegression(max_iter=10000, class_weight='balanced', solver='lbfgs', random_state=RANDOM_STATE)
xgb = XGBClassifier(
    use_label_encoder=False,
    eval_metric='mlogloss',
    num_class=4,
    objective='multi:softprob',
    learning_rate=0.05,
    n_estimators=300,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=RANDOM_STATE
)
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    class_weight='balanced',
    min_samples_split=4,
    min_samples_leaf=2,
    random_state=RANDOM_STATE
)

# === Meta-Level Estimator ===
meta_xgb = XGBClassifier(
    use_label_encoder=False,
    eval_metric='mlogloss',
    num_class=4,
    objective='multi:softprob',
    learning_rate=0.1,
    n_estimators=100,
    max_depth=3,
    random_state=RANDOM_STATE
)

# === Ensemble ===
stacking_clf = StackingClassifier(
    estimators=[('lr', lr), ('xgb', xgb), ('rf', rf)],
    final_estimator=meta_xgb,
    passthrough=True,
    n_jobs=-1
)

# === Full Pipeline ===
pipeline = Pipeline([
    ('features', preprocessor),
    ('clf', stacking_clf)
])

# === Train ===
pipeline.fit(X_train, y_train)

# === Evaluate ===
y_pred = pipeline.predict(X_test)
print("=== Classification Report ===")
print(classification_report(y_test, y_pred, digits=2))

# === Save Model ===
joblib.dump(pipeline, MODEL_OUTPUT_PATH)
print(f"\nModel saved to {MODEL_OUTPUT_PATH}")
