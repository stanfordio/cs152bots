import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re
import joblib
import os

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

def preprocess_text(text):
    """Preprocess text by removing special characters, converting to lowercase, and removing stopwords."""
    if isinstance(text, str):
        # Convert to lowercase
        text = text.lower()
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Tokenize
        tokens = word_tokenize(text)
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        tokens = [token for token in tokens if token not in stop_words]
        return ' '.join(tokens)
    return ''

def load_and_preprocess_data():
    """Load and preprocess the dataset."""
    # Load the datasets
    fake_df = pd.read_csv('DataSet_Misinfo_FAKE.csv')
    true_df = pd.read_csv('DataSet_Misinfo_TRUE.csv')
    
    # Rename columns for consistency
    fake_df.columns = ['index', 'text']
    true_df.columns = ['index', 'text']
    
    # Add labels
    fake_df['label'] = 1  # 1 for fake/misinformation
    true_df['label'] = 0  # 0 for true
    
    # Combine datasets
    df = pd.concat([fake_df, true_df], ignore_index=True)
    
    # Preprocess text
    df['processed_text'] = df['text'].apply(preprocess_text)
    
    return df

def train_classifier(save_model=True):
    """Train and evaluate the misinformation classifier with cross-validation and hyperparameter tuning."""
    # Load and preprocess data
    df = load_and_preprocess_data()
    
    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        df['processed_text'],
        df['label'],
        test_size=0.2,
        random_state=42
    )
    
    # Create a pipeline with TF-IDF vectorizer and classifier
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer()),
        ('clf', LogisticRegression())
    ])
    
    # Define hyperparameter grid
    param_grid = {
        'tfidf__max_features': [3000, 5000, 7000],
        'tfidf__ngram_range': [(1, 1), (1, 2)],
        'clf__C': [0.1, 1.0, 10.0],
        'clf__max_iter': [1000]
    }
    
    # Perform grid search with cross-validation
    grid_search = GridSearchCV(
        pipeline,
        param_grid,
        cv=5,  # 5-fold cross-validation
        scoring='accuracy',
        n_jobs=-1  # Use all available CPU cores
    )
    
    print("Performing grid search with cross-validation...")
    grid_search.fit(X_train, y_train)
    
    # Get best parameters and score
    print("\nBest parameters:", grid_search.best_params_)
    print("Best cross-validation score:", grid_search.best_score_)
    
    # Evaluate on test set
    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_test)
    
    print("\nTest Set Classification Report:")
    print(classification_report(y_test, y_pred))
    print("\nTest Set Accuracy:", accuracy_score(y_test, y_pred))
    
    # Perform additional cross-validation on the best model
    cv_scores = cross_val_score(best_model, X_train, y_train, cv=5)
    print("\nCross-validation scores:", cv_scores)
    print("Mean CV score:", cv_scores.mean())
    print("CV score std:", cv_scores.std())
    
    if save_model:
        # Create models directory if it doesn't exist
        os.makedirs('models', exist_ok=True)
        
        # Save the best model and vectorizer
        model_path = 'models/misinfo_classifier.joblib'
        joblib.dump(best_model, model_path)
        print(f"\nModel saved to {model_path}")
    
    return best_model

def load_model(model_path='classifier/models/misinfo_classifier.joblib'):
    """Load a trained model from file."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    return joblib.load(model_path)

def predict_misinformation(text, model):
    """Predict if a given text is misinformation or not."""
    # Make prediction using the loaded model
    prediction = model.predict([text])[0]
    probability = model.predict_proba([text])[0]
    
    return {
        'is_misinformation': bool(prediction),
        'confidence': float(probability[prediction]),
        'true_probability': float(probability[0]),
        'fake_probability': float(probability[1])
    }

if __name__ == "__main__":
    # # Train the classifier
    # print("Training classifier...")
    # model = train_classifier(save_model=True)
    
    # # Example usage with loaded model
    # test_text = "This is an example text to test the classifier."
    # result = predict_misinformation(test_text, model)
    
    # print("\nExample prediction:")
    # print(f"Text: {test_text}")
    # print(f"Is misinformation: {result['is_misinformation']}")
    # print(f"Confidence: {result['confidence']:.2f}")
    # print(f"True probability: {result['true_probability']:.2f}")
    # print(f"Fake probability: {result['fake_probability']:.2f}") 

    model = load_model()
    prediction = predict_misinformation("Russia did not interfere in the 2016 presidential election", model)
    print(prediction)