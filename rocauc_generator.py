from perspective import perspective_spam_prob
import os
import numpy as np
from sklearn import metrics
import time
from gpt4_classification import gpt4_classify_email
from custom_spam_classifier.custom_classifier import custom_classify_spam
from tqdm import tqdm

##### Helper Functions #####
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

# Rate Limited by Perspective to 1 / second
def getPerspectivePredictions(messages):
    predictions = []
    for msg in tqdm(messages):
        time.sleep(1)
        predictions.append(perspective_spam_prob(msg))
    return np.array(predictions)

def getGPT_Predictions(messages, gpt_func):
    predictions = []
    for msg in tqdm(messages):
        # time.sleep() if needed
        classified = gpt_func(msg)
        if classified == 'spam':
            predictions.append(1)
        else:
            predictions.append(0)
    return np.array(predictions)

##### Generate ROC/AUC for Perspective #####
## Run perspective.perspective_spam_prob(msg) on every message - predictions
def printROC_AUC_Perspective(spam_messages, ham_messages, all_classifiers):
    start_time = time.time()
    print("----- Perspective -----")
    print("Perspective - SPAM")
    spam_predictions = getPerspectivePredictions(spam_messages)
    print("Perspective - HAM")
    ham_predictions = getPerspectivePredictions(ham_messages)

    duration = time.time() - start_time
    print('End Time: {}'.format(duration))
    print('Average Time per Unit: {}'.format(duration / 1000))

    ## Each message should have a corresponding classification and spam_prediction
    ### Run these through sklearn.metrics.roc_curve(y_true, y_score)
    perspective_predictions = np.concatenate((spam_predictions, ham_predictions))
    np.savetxt('perspective_predictions.csv', np.column_stack((all_classifiers,perspective_predictions)), delimiter=',')

    # Generate chart
    fpr, tpr, thresholds = metrics.roc_curve(all_classifiers, perspective_predictions)
    roc_auc = metrics.auc(fpr, tpr)

    np.savetxt('DataAnalysis/perspective_analysis.csv', np.column_stack((np.array(fpr), np.array(tpr), np.array(thresholds))), delimiter=',')


    # Plots the ROC / AUC for Perspective
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

##### Get Confusion Matrix for gpt4-classifier
def printGPT4_Confusion(spam_messages, ham_messages, all_classifiers):
    start_time = time.time()
    print("----- GPT4 -----")

    print("GPT4 - SPAM")
    gpt_4_spam_predictions = getGPT_Predictions(spam_messages, gpt4_classify_email )
    print("GPT4 - HAM")
    gpt_4_ham_predictions = getGPT_Predictions(ham_messages, gpt4_classify_email)

    duration = time.time() - start_time
    print('End Time: {}'.format(duration))
    print('Average Time per Unit: {}'.format(duration / 1000))

    gpt_4_predictions = np.concatenate((gpt_4_spam_predictions, gpt_4_ham_predictions))
    
    np.savetxt('DataAnalysis/gpt4_predictions.csv', np.column_stack((all_classifiers, gpt_4_predictions)), delimiter=',')

    print(metrics.confusion_matrix(all_classifiers, gpt_4_predictions))

##### Get Confusion Matrix for custom gpt3-classifier
def printGPT3_Confusion(spam_messages, ham_messages, all_classifiers):
    start_time = time.time()
    print("----- GPT3 -----")
    
    print("GPT3 - SPAM")
    gpt_3_spam_predictions = getGPT_Predictions(spam_messages, custom_classify_spam)
    print("GPT3 - HAM")
    gpt_3_ham_predictions = getGPT_Predictions(ham_messages, custom_classify_spam)

    duration = time.time() - start_time
    print('End Time: {}'.format(duration))
    print('Average Time per Unit: {}'.format(duration / 1000))

    gpt_3_predictions = np.concatenate((gpt_3_spam_predictions, gpt_3_ham_predictions))
    
    np.savetxt('DataAnalysis/gpt3_predictions.csv', np.column_stack((all_classifiers, gpt_3_predictions)), delimiter=',')

    print(metrics.confusion_matrix(all_classifiers, gpt_3_predictions))


def main():
    test = 5
    ##### Grab Messages + Generate True Classification Matrix #####
    spam_file_path = "DatasetGeneration/spam_emails"
    ham_file_path = "DatasetGeneration/non_spam_emails"

    ## Import messages as an array
    spam_messages = getMessages(spam_file_path)
    ham_messages = getMessages(ham_file_path)

    ## Assign 0 for ham, 1 for spam - true classification
    spam_classifiers = np.array([1] * test) # len(spam_messages))
    ham_classifiers = np.array([0] * test) # len(ham_messages))
    all_classifiers = np.concatenate((spam_classifiers, ham_classifiers))

    # printGPT4_Confusion(spam_messages, ham_messages, all_classifiers)
    # printROC_AUC_Perspective(spam_messages, ham_messages, all_classifiers)
    printGPT3_Confusion(spam_messages[:test], ham_messages[:test], all_classifiers)

if __name__ == '__main__':
    main()