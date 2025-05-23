from flask import Flask, request, jsonify
import joblib  # or pickle depending on our model
import os

app = Flask(__name__)

# load model
model = joblib.load("your_model.pkl")  

# we only need one endpoitn which takes some text taht is the message content (in json)
@app.route("/classify", methods=["POST"])
def predict():
    data = request.json
    message = data.get("message", "")
    prediction = model.predict([message])[0]
    confidence = max(model.predict_proba([message])[0]) 
    return jsonify({"classification": prediction, "confidence_score": float(confidence)})
