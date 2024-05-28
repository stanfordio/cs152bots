import shap
from transformers import BertTokenizer, BertForSequenceClassification
import torch
class ScamClassifier:
    def __init__(self):
        self.model = BertForSequenceClassification.from_pretrained('./model/scam_detection_model')
        self.tokenizer = BertTokenizer.from_pretrained('./model/scam_detection_tokenizer')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        self.LABEL_MAPPING = {0: 'Not a Scam', 1: 'Scam'}
    def batch_predict_scammer(self, texts, batch_size=32):
        predictions = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Encode the batch of texts
            encodings = self.tokenizer.batch_encode_plus(
                batch_texts,
                max_length=512,
                truncation=True,
                padding='max_length',
                return_tensors='pt'
            )
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)

            # Make prediction
            with torch.no_grad():
                outputs = self.model(input_ids, attention_mask=attention_mask)
                probabilities = torch.softmax(outputs.logits, dim=-1)
                predicted_classes = torch.argmax(probabilities, dim=1).cpu().numpy()

            predictions.extend(predicted_classes)

        return [self.LABEL_MAPPING[pred] for pred in predictions]


    def predict_scammer(self, text):
        # Encode the text
        encoding = self.tokenizer.encode_plus(
            text,
            max_length=512,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        # Make prediction
        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask=attention_mask)
            probabilities = torch.softmax(outputs.logits, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=1).cpu().item()

        return self.LABEL_MAPPING[predicted_class]

