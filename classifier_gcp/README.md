this folder will be for the code in GCP that runs our classifier

- main.py: Flask server
- requirements.txt: dependencies
- Dockerfile: creates the python runtime for our code. I probably need to update this. also not sure what version of python to run but I assume 3.12 is fine.

TODOs:
- once rhea gets the model trained, get it locally and then upload to gcp:
`gsutil cp path/to/your_model.pkl gs://pol-disinfo-classifier/`
- deploy cloud run instance: 
    ```
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/discord-classifier
    gcloud run deploy discord-classifier \
  --image gcr.io/YOUR_PROJECT_ID/discord-classifier \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated
  ```
- use the public URL that is given for our code


we can curl the endpoint using this:
```
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"message": "this is a test"}' \
     https://your-service-url.a.run.app/classify

```