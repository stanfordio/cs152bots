import joblib
import re
from nltk.tokenize import word_tokenize
import string

# message = "let's catch some online groomers lol"


def predict_classify(message):
    #preprocessing function
    def preprocess_text(text):
        if text:
            text = text.strip()
            text = re.sub(r'<email/>', '', text)
            text = text.translate(str.maketrans('', '', string.punctuation))
            text = text.lower()
            tokens = word_tokenize(text)
            return ' '.join(tokens)
        return ''

    #Load models and the vectorizer
    nb_model = joblib.load('classifiers/naive_bayes_model.pkl')
    lr_model = joblib.load('classifiers/logistic_regression_model.pkl')
    vectorizer = joblib.load('classifiers/tfidf_vectorizer.pkl')

    #preprocess
    cleaned_message = preprocess_text(message)
    X_new = vectorizer.transform([cleaned_message])

    y_pred_nb = nb_model.predict(X_new)
    y_pred_lr = lr_model.predict(X_new)
    # print(y_pred_nb[0], y_pred_lr[0])
    return y_pred_nb[0], y_pred_lr[0]

# predict_classify(message)