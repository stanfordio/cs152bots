import xml.etree.ElementTree as ET
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import word_tokenize
import string
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib

#parse XML file
def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    data = []
    for conversation in root.findall('conversation'):
        convo_id = conversation.get('id')
        for message in conversation.findall('message'):
            author_elem = message.find('author')
            author_id = author_elem.text.strip() if author_elem is not None else None
            line_num = message.get('line')
            text_elem = message.find('text')
            text = text_elem.text
            data.append([convo_id, author_id, line_num, text])
    return data

# create DataFrame for Training Data
train_data = parse_xml('./pan12/pan12 train/pan12-sexual-predator-identification-training-corpus-2012-05-01.xml')
df_train = pd.DataFrame(train_data, columns=['conversation_id', 'author_id', 'line_num', 'text'])

#label Training Data
with open('./pan12/pan12 train/pan12-sexual-predator-identification-training-corpus-predators-2012-05-01.txt') as f:
    predators = f.read().splitlines()
with open('./pan12/pan12 train/pan12-sexual-predator-identification-diff.txt') as f:
    predators2 = f.read().splitlines()
    predators2 = [predator.split('\t') for predator in predators2]

df_train['label'] = df_train['author_id'].apply(lambda x: 1 if x in predators else 0)

for index, row in df_train.iterrows():
    if (row['conversation_id'], row['line_num']) in predators2:
        df_train.at[index, 'label'] = 1

#preprocess text
def preprocess_text(text):
    if text:
        text = text.strip()
        text = re.sub(r'<email/>', '', text)
        text = text.translate(str.maketrans('', '', string.punctuation))
        text = text.lower()
        tokens = word_tokenize(text)
        return ' '.join(tokens)
    return ''

df_train['cleaned_text'] = df_train['text'].apply(preprocess_text)

#feature extraction
vectorizer = TfidfVectorizer()
X_train = vectorizer.fit_transform(df_train['cleaned_text'])
y_train = df_train['label']

df_train.to_csv('preprocessed_traindata.csv', index=False)

# Process Test Data
test_data = parse_xml('./pan12/pan12 test/pan12-sexual-predator-identification-test-corpus-2012-05-17.xml')
df_test = pd.DataFrame(test_data, columns=['conversation_id', 'author_id', 'line_num', 'text'])

#label data
with open('./pan12/pan12 test/pan12-sexual-predator-identification-groundtruth-problem1.txt') as f:
    test_predators = f.read().splitlines()
with open('./pan12/pan12 test/pan12-sexual-predator-identification-groundtruth-problem2.txt') as f:
    test_predators2 = f.read().splitlines()
    test_predators2 = [predator.split('\t') for predator in test_predators2]

df_test['label'] = df_test['author_id'].apply(lambda x: 1 if x in test_predators else 0)

for index, row in df_test.iterrows():
    if (row['conversation_id'], row['line_num']) in test_predators2:
        df_test.at[index, 'label'] = 1

# preprocess data
df_test['cleaned_text'] = df_test['text'].apply(preprocess_text)

#feature extraction
X_test = vectorizer.transform(df_test['cleaned_text'])
y_test = df_test['label']

df_test.to_csv('preprocessed_testdata.csv', index=False)

#train naive bayes classifer 
nb_model = MultinomialNB()
nb_model.fit(X_train, y_train)

#evaluate naive bayes classifier
y_pred_nb = nb_model.predict(X_test)
print("Naive Bayes Model")
print(f'Accuracy: {accuracy_score(y_test, y_pred_nb)}')
print(f'Classification Report:\n{classification_report(y_test, y_pred_nb)}')

#train logisctic regression classifier
lr_model = LogisticRegression(max_iter=1000)
lr_model.fit(X_train, y_train)

#evaluate logistic reg classifier
y_pred_lr = lr_model.predict(X_test)
print("Logistic Regression Model")
print(f'Accuracy: {accuracy_score(y_test, y_pred_lr)}')
print(f'Classification Report:\n{classification_report(y_test, y_pred_lr)}')

#save model 
joblib.dump(nb_model, 'naive_bayes_model.pkl')
joblib.dump(lr_model, 'logistic_regression_model.pkl')
joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')
