from PIL import Image
import requests
from io import BytesIO
from transformers import AutoFeatureExtractor, AutoModelForImageClassification
extractor = AutoFeatureExtractor.from_pretrained("nickmuchi/vit-finetuned-cats-dogs")

model = AutoModelForImageClassification.from_pretrained("nickmuchi/vit-finetuned-cats-dogs")

def image_classifier(url):
  response = requests.get(url)
  img = Image.open(BytesIO(response.content))

  inputs = extractor(images=img, return_tensors="pt")

  outputs = model(**inputs)
  logits = outputs.logits

  predicted_class_idx = logits.argmax(-1).item()
  return predicted_class_idx == 0


