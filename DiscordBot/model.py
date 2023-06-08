__author__ = "Yifan Zhang (yzhang@hbku.edu.qa)"
__copyright__ = "Copyright (C) 2021, Qatar Computing Research Institute, HBKU, Doha"


from dataclasses import dataclass
from typing import Optional, Tuple
import torch
from torch import nn
from torch.nn.functional import sigmoid
from transformers import BertPreTrainedModel, BertModel
from transformers.file_utils import ModelOutput

#justin
PROPOGANDA_SENTINEL = "contains_propoganda"
NO_LABEL = ""

TOKEN_TAGS = (
    "<PAD>", NO_LABEL, 
    "Name_Calling,Labeling", "Repetition", "Slogans", "Appeal_to_fear-prejudice", "Doubt",
    "Exaggeration,Minimisation", "Flag-Waving", "Loaded_Language",
    "Reductio_ad_hitlerum", "Bandwagon",
    "Causal_Oversimplification", "Obfuscation,Intentional_Vagueness,Confusion", "Appeal_to_Authority", "Black-and-White_Fallacy",
    "Thought-terminating_Cliches", "Red_Herring", "Straw_Men", "Whataboutism"
)


#justin edits
SEQUENCE_TAGS = ("no_propoganda", PROPOGANDA_SENTINEL)


@dataclass
class TokenAndSequenceJointClassifierOutput(ModelOutput):
    loss: Optional[torch.FloatTensor] = None
    token_logits: torch.FloatTensor = None
    sequence_logits: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None


class BertForTokenAndSequenceJointClassification(BertPreTrainedModel):

    def __init__(self, config):
        super().__init__(config)
        self.num_token_labels = 20
        self.num_sequence_labels = 2

        self.token_tags = TOKEN_TAGS
        self.sequence_tags = SEQUENCE_TAGS 

        self.alpha = 0.9

        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.ModuleList([
            nn.Linear(config.hidden_size, self.num_token_labels),
            nn.Linear(config.hidden_size, self.num_sequence_labels),
        ])
        self.masking_gate = nn.Linear(2, 1)

        self.init_weights()
        self.merge_classifier_1 = nn.Linear(self.num_token_labels + self.num_sequence_labels, self.num_token_labels)

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=True,
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
        )

        sequence_output = outputs[0]
        pooler_output = outputs[1]

        sequence_output = self.dropout(sequence_output)
        token_logits = self.classifier[0](sequence_output)

        pooler_output = self.dropout(pooler_output)
        sequence_logits = self.classifier[1](pooler_output)

        gate = torch.sigmoid(self.masking_gate(sequence_logits))

        gates = gate.unsqueeze(1).repeat(1, token_logits.size()[1], token_logits.size()[2])

        weighted_token_logits = torch.mul(gates, token_logits)

        logits = [weighted_token_logits, sequence_logits]

        loss = None
        if labels is not None:
            criterion = nn.CrossEntropyLoss(ignore_index=0)
            binary_criterion = nn.BCEWithLogitsLoss(pos_weight=torch.Tensor([3932/14263]).cuda())
            loss_fct = CrossEntropyLoss()
            weighted_token_logits = weighted_token_logits.view(-1, weighted_token_logits.shape[-1])
            sequence_logits = sequence_logits.view(-1, sequence_logits.shape[-1])

            token_loss = criterion(weighted_token_logits, labels)
            sequence_label = torch.LongTensor([1] if any([label > 0 for label in labels]) else [0])
            sequence_loss = binary_criterion(sequence_logits, sequence_label)

            loss = self.alpha*loss[0] + (1-self.alpha)*loss[1]

        if not return_dict:
            output = (logits,) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return TokenAndSequenceJointClassifierOutput(
            loss=loss,
            token_logits=weighted_token_logits,
            sequence_logits=sequence_logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )


