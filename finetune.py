from google.cloud import aiplatform

# REPLACE with your project ID
project_id = "your_project_id"

# REPLACE with the region where your Vertex AI resources are located
location = "us-central1"  # Replace with your desired region

# REPLACE with the name of your training dataset (stored in Vertex AI)
training_dataset_name = "gs://your-bucket/path/to/your/training_dataset.jsonl"

# REPLACE with the name of your validation dataset (stored in Vertex AI)
validation_dataset_name = "gs://your-bucket/path/to/your/validation_dataset.jsonl"

# REPLACE with the name of the base Gemini model you want to fine-tune
base_model_name = "projects/google-ai-platform/locations/us-central1/models/gemini-1.0-pro-002" 

# REPLACE with a name for your custom fine-tuned model
display_name = "my_custom_gemini_model"

def fine_tune_gemini(project_id, location, training_dataset_name, validation_dataset_name, base_model_name, display_name):
  """Fine-tunes a Gemini model using Vertex AI.

  Args:
      project_id: Your GCP project ID.
      location: The region where your Vertex AI resources are located.
      training_dataset_name: The name of your training dataset stored in Vertex AI (GCS path).
      validation_dataset_name: The name of your validation dataset stored in Vertex AI (GCS path).
      base_model_name: The name of the base Gemini model to fine-tune.
      display_name: The name you want to give to your custom fine-tuned model.
  """

  aiplatform.init(project=project_id, location=location)

  # Define the training job configuration
  training_job = aiplatform.training_jobs.CustomTrainingJob(
      display_name=display_name,
      base_model=base_model_name,
      # Set the task type to 'text-classification' for supervised tuning
      task_type="text-classification",
      # Set your training and validation dataset paths
      dataset_spec={
          "data_sources": [
              {"source": training_dataset_name},
              {"source": validation_dataset_name, "role": "validation"}
          ]
      },
      # Set the container specification (adapt based on your needs)
      container_spec={
          "image_uri": "gcr.io/google-research/fine-tune-gemini",
          "environment_variables": {"tuning_mode": "supervised"}
      }
  )

  # Run the training job
  training_run = training_job.run()
  print(f"Fine-tuning job submitted: {training_run.name}")

if __name__ == "__main__":
  fine_tune_gemini(project_id, location, training_dataset_name, validation_dataset_name, base_model_name, display_name)
