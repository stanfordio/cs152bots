import requests

data = {
    "message": "Joe Biden banned all beef products in the US.",
    "justification": "A claim on a partisan blog.",
    "metadata": "Biden politics diet USA",
    "credit_score": 0.5
}


response = requests.post("http://127.0.0.1:5000/classify", json=data)
print(response.json())