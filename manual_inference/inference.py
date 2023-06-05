import torch
from pytorch_pretrained_bert import BertTokenizer

num_task = 2
masking = 1
hier = 0

tokenizer = BertTokenizer.from_pretrained('bert-base-cased', do_lower_case=False)
VOCAB, tag2idx, idx2tag = [], [], []

#sentence classification
VOCAB.append(("<PAD>", "O", "Name_Calling,Labeling", "Repetition", "Slogans", "Appeal_to_fear-prejudice", "Doubt"
                , "Exaggeration,Minimisation", "Flag-Waving", "Loaded_Language"
                , "Reductio_ad_hitlerum", "Bandwagon"
                , "Causal_Oversimplification", "Obfuscation,Intentional_Vagueness,Confusion", "Appeal_to_Authority", "Black-and-White_Fallacy"
                , "Thought-terminating_Cliches", "Red_Herring", "Straw_Men", "Whataboutism"))
VOCAB.append(("Non-prop", "Prop"))

for i in range(num_task):
    tag2idx.append({tag:idx for idx, tag in enumerate(VOCAB[i])})
    idx2tag.append({idx:tag for idx, tag in enumerate(VOCAB[i])})

tokenizer = BertTokenizer.from_pretrained('bert-base-cased', do_lower_case=False)

def preprocess(sentence):
    words = sentence

    x, is_heads = [], [] # list of ids
    seqlen = 0

    for w in words:
        tokens = tokenizer.tokenize(w) if w not in ("[CLS]", "[SEP]") else [w]
        xx = tokenizer.convert_tokens_to_ids(tokens)

        is_head = [1] + [0]*(len(tokens) - 1)
        if len(xx) < len(is_head):
            xx = xx + [100] * (len(is_head) - len(xx))

        t = [t] + [t] * (len(tokens) - 1)

        x.extend(xx)
        is_heads.extend(is_head)
        seqlen += len(t)


    att_mask = [1] * seqlen
    return words, x, is_heads, att_mask, seqlen

def pad(batch):
    f = lambda x: [sample[x] for sample in batch]
    words = f(0)
    is_heads = f(2)
    seqlen = f(-1)
    maxlen = 210

    f = lambda x, seqlen: [sample[x] + [0] * (seqlen - len(sample[x])) for sample in batch] # 0: <pad>
    x = torch.LongTensor(f(1, maxlen))

    att_mask = f(3, maxlen)
    
    return words, x, is_heads, att_mask, seqlen

def eval(model, sentence):
    data = pad([preprocess(sentence)])

    Words, Is_heads = [], []
    Tags = [[] for _ in range(num_task)]
    Y = [[] for _ in range(num_task)]
    Y_hats = [[] for _ in range(num_task)]
    with torch.no_grad():
        for _ , batch in enumerate(data):
            words, x, is_heads, att_mask, tags, y, seqlens = batch
            att_mask = torch.Tensor(att_mask)
            logits, y_hats = model(x, attention_mask=att_mask) # logits: (N, T, VOCAB), y: (N, T)
      
            loss = []
            if num_task == 2 or masking:
                for i in range(num_task):
                    logits[i] = logits[i].view(-1, logits[i].shape[-1]) # (N*T, 2)
                y[0] = y[0].view(-1)
                y[1] = y[1].float()
            else:
                for i in range(num_task):
                    logits[i] = logits[i].view(-1, logits[i].shape[-1]) # (N*T, 2)
                    y[i] = y[i].view(-1)

            Words.extend(words)
            Is_heads.extend(is_heads)

            for i in range(num_task):
                Tags[i].extend(tags[i])
                Y[i].extend(y[i].numpy().tolist())
                Y_hats[i].extend(y_hats[i].numpy().tolist())

    y_hats, preds = [[] for _ in range(num_task)], [[] for _ in range(num_task)]
    for words, is_heads, tags[0], tags[1], y_hats[0], y_hats[1] in zip(Words, Is_heads, *Tags, *Y_hats):
        y_hats[0] = [hat for head, hat in zip(is_heads, y_hats[0]) if head == 1]
        preds[0] = [idx2tag[0][hat] for hat in y_hats[0]]
        preds[1] = idx2tag[1][y_hats[1]]
        
        print(words, preds[0], preds[1])
          

model = torch.load("20230605-053615.pt")
model.eval()
eval(model, "Donald Trump is the greatst president to ever live")



