from flask import Flask, request, jsonify
from pytorch_pretrained_bert import BertTokenizer, BertModel, BertConfig
import torch
import torch.nn as nn
import torch.nn.functional as F

# Import your model definition (or paste class directly)
from model import BertForSequenceClassification  # or define directly below if easier

app = Flask(__name__)

# Load tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# BERT config (must match your training config)
config = BertConfig(vocab_size_or_config_json_file=32000, hidden_size=768,
                    num_hidden_layers=12, num_attention_heads=12, intermediate_size=3072)

# Load model and weights
model = BertForSequenceClassification(num_labels=2)
model.load_state_dict(torch.load("bert_model_finetuned.pth", map_location=torch.device('cpu')))
model.eval()

def preprocess(text, max_len):
    tokens = tokenizer.tokenize(text if text else "None")
    tokens = tokens[:max_len]
    token_ids = tokenizer.convert_tokens_to_ids(tokens)
    padded = token_ids + [0] * (max_len - len(token_ids))
    return torch.tensor(padded).unsqueeze(0)  # shape: (1, max_len)

@app.route("/classify", methods=["POST"])
def predict():
    data = request.json

    statement = data.get("message", "")
    justification = data.get("justification", "")
    metadata = data.get("metadata", "")
    credit = data.get("credit_score", 0.5)

    input_ids1 = preprocess(statement, max_len=64)
    input_ids2 = preprocess(justification, max_len=256)
    input_ids3 = preprocess(metadata, max_len=32)
    credit_tensor = torch.tensor([credit] * 2304).unsqueeze(0)  # shape (1, 2304)

    with torch.no_grad():
        logits = model(input_ids1, input_ids2, input_ids3, credit_tensor)
        probs = F.softmax(logits, dim=1)
        confidence = probs[0][1].item()
        prediction = "misinformation" if confidence > 0.5 else "factual"

    return jsonify({
        "classification": prediction,
        "confidence_score": round(confidence, 4)
    })

if __name__ == "__main__":
    app.run(debug=True)