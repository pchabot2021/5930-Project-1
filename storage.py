from google.cloud import datastore, storage
import os
import time

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sonic-base-449423-g4")

datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

BUCKET_NAME = "chabotproject1bucket"

def upload_file(bucket_name, file_stream, destination_filename):
    """Uploads file to Google Cloud Storage and returns a public URL."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_filename)
    blob.upload_from_file(file_stream)
    
    # Return the public URL for the uploaded file
    return f"https://storage.googleapis.com/{bucket_name}/{destination_filename}"

def add_db_entry(object):
    """Stores file metadata in Google Cloud Datastore."""
    entity = datastore.Entity(key=datastore_client.key('photos'))
    entity.update(object)
    datastore_client.put(entity)