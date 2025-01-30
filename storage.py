from google.cloud import datastore, storage
import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sonic-base-449423-g4")

datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

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

def delete_file(bucket_name, blob_name):
    """Deletes a file from Google Cloud Storage and its metadata from Datastore."""
    # Delete the file from GCS
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()

    # Delete the corresponding metadata from Datastore
    query = datastore_client.query(kind='photos')
    query.add_filter('name', '=', blob_name)
    results = list(query.fetch())
    for entity in results:
        datastore_client.delete(entity.key)