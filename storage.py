from google.cloud import datastore, storage
import os
import time
from flask import Flask, request, render_template, redirect
from werkzeug.utils import secure_filename

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sonic-base-449423-g4")

datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

BUCKET_NAME = "chabotproject1bucket"

def upload_file(bucket_name, file_stream, destination_filename):
    """Uploads file to Google Cloud Storage."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_filename)
    blob.upload_from_file(file_stream)
    return f"gs://{bucket_name}/{destination_filename}"

def add_db_entry(object):
    """Stores file metadata in Google Cloud Datastore."""
    entity = datastore.Entity(key=datastore_client.key('photos'))
    entity.update(object)
    datastore_client.put(entity)

# Flask App
app = Flask(__name__)

@app.get("/")
def index():
    """Fetches and displays uploaded photos."""
    query = datastore_client.query(kind='photos')
    photos = list(query.fetch())
    return render_template('index.html', photos=photos)

@app.post("/upload")
def upload_image():
    """Handles image uploads and stores metadata."""
    if 'file' not in request.files:
        return redirect('/')
    
    file = request.files['file']
    if file.filename == '':
        return redirect('/')
    
    if file:
        filename = secure_filename(file.filename)
        gcs_path = upload_file(BUCKET_NAME, file, filename)
        
        entity = {
            "name": filename,
            "gcs_path": gcs_path,
            "timestamp": int(time.time())
        }
        add_db_entry(entity)

    return redirect('/')

if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)