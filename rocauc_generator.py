from perspective import perspective_spam_prob
import os
import numpy as np
from sklearn import metrics

## Import messages as an array
spam_file_path = "DatasetGeneration/spam_emails"
ham_file_path = "DatasetGeneration/non_spam_emails"

def getMessages(path):
    owd = os.getcwd()
    os.chdir(path)
    
    messages=[]
    for file in os.listdir():
        # Check whether file is in text format or not
        if file.endswith(".txt"):
            msg = open(file, "r")
            messages.append(msg.read())
            msg.close()

    os.chdir(owd)
    return messages

spam_messages = getMessages(spam_file_path)
ham_messages = getMessages(ham_file_path)

## Assign 0 for ham, 1 for spam - true classification
spam_classifiers = np.array([1] * len(spam_messages))
ham_classifiers = np.array([0] * len(ham_messages))

## Run perspective.perspective_spam_prob(msg) on every message - predictions
spam_predictions = np.array(list(map(perspective_spam_prob, spam_messages)))
ham_predictions = np.array(list(map(perspective_spam_prob, ham_messages)))

## Each message should have a corresponding classification and spam_prediction
### Run these through sklearn.metrics.roc_curve(y_true, y_score)
all_classifiers = np.concatenate((spam_classifiers, ham_classifiers))
all_predictions = np.concatenate((spam_predictions, ham_predictions))
fpr, tpr, thresholds = metrics.roc_curve(all_classifiers, all_predictions)
roc_auc = metrics.auc(fpr, tpr)

# method I: plt
import matplotlib.pyplot as plt
plt.title('Receiver Operating Characteristic')
plt.plot(fpr, tpr, 'b', label = 'AUC = %0.2f' % roc_auc)
plt.legend(loc = 'lower right')
plt.plot([0, 1], [0, 1],'r--')
plt.xlim([0, 1])
plt.ylim([0, 1])
plt.ylabel('True Positive Rate')
plt.xlabel('False Positive Rate')
plt.show(block=True)