from transformers import BertTokenizerFast
from model import BertForTokenAndSequenceJointClassification, PROPOGANDA_SENTINEL, NO_LABEL
import torch
import sys


tokenizer = BertTokenizerFast.from_pretrained('bert-base-cased')
model = BertForTokenAndSequenceJointClassification.from_pretrained(
    "QCRI/PropagandaTechniquesAnalysis-en-BERT",
    revision="v0.1.0",
)

def predict_propoganda(sentence):
    inputs = tokenizer.encode_plus(sentence, return_tensors="pt")
    outputs = model(**inputs)
    sequence_class_index = torch.argmax(outputs.sequence_logits, dim=-1)
    sequence_class = model.sequence_tags[sequence_class_index[0]]
    token_class_index = torch.argmax(outputs.token_logits, dim=-1)
    tags = [model.token_tags[i] for i in token_class_index[0].tolist()[1:-1]]
    
    return sequence_class == PROPOGANDA_SENTINEL, set([t for t in tags if t != NO_LABEL])

if __name__ == '__main__':
    print(predict_propoganda(sys.argv[1]))