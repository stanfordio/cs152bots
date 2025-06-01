import torch
import torch.nn as nn
from pytorch_pretrained_bert import BertModel, BertConfig

# Optional layer norm class (not currently used, but included for completeness)
class BertLayerNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-12):
        super(BertLayerNorm, self).__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size))
        self.variance_epsilon = eps

    def forward(self, x):
        u = x.mean(-1, keepdim=True)
        s = (x - u).pow(2).mean(-1, keepdim=True)
        x = (x - u) / torch.sqrt(s + self.variance_epsilon)
        return self.weight * x + self.bias


# Main classifier model class
class BertForSequenceClassification(nn.Module):
    def __init__(self, num_labels=2):
        super(BertForSequenceClassification, self).__init__()
        self.num_labels = num_labels
        self.config = BertConfig(vocab_size_or_config_json_file=32000, hidden_size=768,
                                 num_hidden_layers=12, num_attention_heads=12, intermediate_size=3072)
        self.bert = BertModel.from_pretrained('bert-base-uncased')
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.config.hidden_size * 3, num_labels)
        nn.init.xavier_normal_(self.classifier.weight)

    def forward_once(self, input_ids, token_type_ids=None, attention_mask=None):
        _, pooled_output = self.bert(input_ids, token_type_ids, attention_mask, output_all_encoded_layers=False)
        pooled_output = self.dropout(pooled_output)
        return pooled_output

    def forward(self, input_ids1, input_ids2, input_ids3, credit_sc):
        output1 = self.forward_once(input_ids1)
        output2 = self.forward_once(input_ids2)
        output3 = self.forward_once(input_ids3)

        out = torch.cat((output1, output2, output3), dim=1)
        out = out + credit_sc  # add credit score vector

        logits = self.classifier(out)
        return logits