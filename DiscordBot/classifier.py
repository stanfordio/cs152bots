from transformers import AutoModel
from transformers.modeling_outputs import SequenceClassifierOutput
from torch import nn

class TextClassifier(nn.Module):
    def __init__(
        self,
        base_model_name="Alibaba-NLP/gte-multilingual-base",
        num_classes=2,
        freeze_base_model=False,
    ):
        super().__init__()
        self.base_model = AutoModel.from_pretrained(base_model_name, trust_remote_code=True)
        if freeze_base_model:
            for p in self.base_model.parameters():
                p.requires_grad = False
        base_model_hidden_size = self.base_model.config.hidden_size
        self.head = nn.Linear(base_model_hidden_size, num_classes)
        self.loss_fn = nn.CrossEntropyLoss()

    def forward(
        self,
        input_ids,
        attention_mask=None,
        labels=None,
    ):
        outputs = self.base_model(input_ids=input_ids, attention_mask=attention_mask)
        hidden_states = outputs.last_hidden_state
        if len(hidden_states.shape) == 3:
            hidden_states = hidden_states[:, 0]
        logits = self.head(hidden_states)
        loss = None
        if labels is not None:
            loss = self.loss_fn(logits, labels)
        return SequenceClassifierOutput(
            loss=loss,
            logits=logits
        )