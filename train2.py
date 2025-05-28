# === Work in Progress === #

import pandas as pd
import numpy as np
import re
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, random_split
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

# === Config ===
DATA_PATH = "all_data.csv"
RANDOM_STATE = 42
BATCH_SIZE = 16
EPOCHS = 50
LEARNING_RATE = 1e-4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# === Load Data ===
df = pd.read_csv(DATA_PATH)
df["Severity"] = df["Severity"].astype(int)

# === Manual Features ===
def count_urgency_words(text):
    return len(re.findall(r"\b(now|urgent|immediately|soon|timer|profit|deadline|tonight|risk|guarantee|double)\b", text.lower()))

def extract_manual_features(texts):
    features = []
    for x in texts:
        features.append([
            len(x),
            len(x.split()),
            len(re.findall(r"\$\d+", x)),
            count_urgency_words(x),
            sum(c in "!?.;" for c in x) / (len(x) + 1),
            x.count('\n') / (len(x) + 1)
        ])
    return np.array(features)

manual_features = extract_manual_features(df["Conversation"].tolist())
scaler = StandardScaler()
manual_scaled = scaler.fit_transform(manual_features)

# === BERT Embeddings ===
bert_model = SentenceTransformer('all-mpnet-base-v2')
bert_embeddings = bert_model.encode(df["Conversation"].tolist(), show_progress_bar=True)

# === Final Features ===
X = np.concatenate([bert_embeddings, manual_scaled], axis=1)
y = df["Severity"].values - 1  # classes 0–3

# === Train/Test Split ===
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2, random_state=RANDOM_STATE)
train_data = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train))
test_data = TensorDataset(torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test))
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_data, batch_size=BATCH_SIZE)

# === Model ===
class ResidualMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=768, num_classes=4):
        super().__init__()
        self.fc_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.BatchNorm1d(hidden_dim)
        )
        self.block1 = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.BatchNorm1d(hidden_dim)
        )
        self.block2 = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.BatchNorm1d(hidden_dim)
        )
        self.out = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        x = self.fc_in(x)
        x = x + self.block1(x)
        x = x + self.block2(x)
        return self.out(x)

model = ResidualMLP(input_dim=X.shape[1]).to(DEVICE)
optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
criterion = nn.CrossEntropyLoss()

# === Training Loop ===
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for xb, yb in train_loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        optimizer.zero_grad()
        pred = model(xb)
        loss = criterion(pred, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {total_loss:.4f}")

# === Evaluation ===
model.eval()
all_preds, all_targets = [], []
with torch.no_grad():
    for xb, yb in test_loader:
        xb = xb.to(DEVICE)
        logits = model(xb)
        preds = torch.argmax(logits, dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(yb.numpy())

print("\n=== Classification Report ===")
print(classification_report(all_targets, all_preds, digits=2))
