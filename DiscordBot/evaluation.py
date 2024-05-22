import pandas as pd
import time
from perspective import check_hate_speech

hatemoji_df = pd.read_csv('../data/hatemojicheck.csv')

def evaluate_perspective_model(data):
    results = {}
    correct, true_pos, true_neg, false_pos, false_neg = 0, 0, 0, 0, 0
    total = len(data)
    for index, row in data.iterrows():
        pred_hate_speech = check_hate_speech(row.text)
        if pred_hate_speech == row.label_gold:
            correct += 1
        if pred_hate_speech and row.label_gold:  # we predicted hate speech and it is
            true_pos += 1
        if not pred_hate_speech and not row.label_gold:  # we predicted not hate speech and it's not
            true_neg += 1
        if pred_hate_speech and not row.label_gold:  # we predicted hate speech but it's not
            false_pos += 1
        if not pred_hate_speech and row.label_gold:  # we predicted not hate speech but it is
            false_neg += 1
        if index % 60 == 0:  # avoid perspective quota limits
            time.sleep(60)
    results["accuracy"] = correct / total
    results["true_positives"] = true_pos
    results["true_negatives"] = true_neg
    results["false_positives"] = false_pos
    results["false_negatives"] = false_neg
    results["precision"] = true_pos / (true_pos + false_pos)
    results["recall"] = true_pos / (true_pos + false_neg)
    results["prevalence"] = false_neg / total
    return results
