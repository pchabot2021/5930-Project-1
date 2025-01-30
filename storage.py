from google.cloud import datastore, storage
import os

# Fetch project ID from environment variables (safer than hardcoding)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sonic-base-449423-g4")  # Fallback to your ID

datastore_client = datastore.Client(project=PROJECT_ID)  # ✅ Project ID added
storage_client = storage.Client(project=PROJECT_ID)      # ✅ Project ID added

def upload_file(bucket_name, file_stream, destination_filename):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_filename)
    blob.upload_from_file(file_stream)
    blob.make_public()
    return blob.public_url

def add_db_entry(object):
    entity = datastore.Entity(key=datastore_client.key('photos'))
    entity.update(object)
    datastore_client.put(entity)