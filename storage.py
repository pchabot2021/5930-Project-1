from google.cloud import datastore, storage
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")

def get_storage_client():
    """Get storage client with appropriate credentials based on environment"""
    return storage.Client(project=PROJECT_ID)

def get_datastore_client():
    """Get datastore client with appropriate credentials"""
    return datastore.Client(project=PROJECT_ID)

storage_client = get_storage_client()
datastore_client = get_datastore_client()

def upload_file(bucket_name, file_stream, destination_filename):
    """Uploads file to Google Cloud Storage."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_filename)
        blob.upload_from_file(file_stream)
        return destination_filename
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise

def get_file_stream(bucket_name, blob_name):
    """Gets a file from Google Cloud Storage as a byte stream."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Check if blob exists
        if not blob.exists():
            logger.warning(f"File not found: {blob_name}")
            raise FileNotFoundError(f"File not found")
        
        # Download as bytes
        downloaded_blob = blob.download_as_bytes()
        return downloaded_blob
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise

def get_content_type(filename):
    """Determine content type based on file extension."""
    lower_filename = filename.lower()
    if lower_filename.endswith(('.jpg', '.jpeg')):
        return 'image/jpeg'
    elif lower_filename.endswith('.png'):
        return 'image/png'
    elif lower_filename.endswith('.gif'):
        return 'image/gif'
    elif lower_filename.endswith('.webp'):
        return 'image/webp'
    elif lower_filename.endswith('.bmp'):
        return 'image/bmp'
    else:
        return 'application/octet-stream'

def add_db_entry(object):
    """Stores file metadata in Google Cloud Datastore."""
    try:
        entity = datastore.Entity(key=datastore_client.key('photos'))
        entity.update(object)
        datastore_client.put(entity)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise

def delete_file(bucket_name, blob_name):
    """Deletes a file from Google Cloud Storage and its metadata from Datastore."""
    try:
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
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise