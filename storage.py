from google.cloud import datastore, storage
import os
import time
from flask import Flask, request, render_template, redirect
from werkzeug.utils import secure_filename

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sonic-base-449423-g4")

datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

BUCKET_NAME = "chabotproject1bucket"

def upload_file(bucket_name, file_stream, destination_filename, allowed_users=None):
    """
    Uploads file to Google Cloud Storage with specific access permissions.
    allowed_users: list of user emails who should have access
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_filename)
    blob.upload_from_file(file_stream)

    # Set object access control
    if allowed_users:
        for user_email in allowed_users:
            blob.acl.user(user_email).grant_read()
            blob.acl.save()

    return f"gs://{bucket_name}/{destination_filename}"

def add_db_entry(object):
    """Stores file metadata in Google Cloud Datastore."""
    entity = datastore.Entity(key=datastore_client.key('photos'))
    entity.update(object)
    datastore_client.put(entity)

def update_file_permissions(bucket_name, filename, new_users):
    """Updates the access permissions for a specific file."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    
    # Reset ACL to private
    blob.acl.all().revoke_read()
    blob.acl.save()
    
    # Add new permissions
    for user_email in new_users:
        blob.acl.user(user_email).grant_read()
    blob.acl.save()

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
    
    # Get allowed users from form
    allowed_users = request.form.get('allowed_users', '').split(',')
    allowed_users = [email.strip() for email in allowed_users if email.strip()]
    
    if file:
        filename = secure_filename(file.filename)
        gcs_path = upload_file(BUCKET_NAME, file, filename, allowed_users)
        
        entity = {
            "name": filename,
            "gcs_path": gcs_path,
            "allowed_users": allowed_users,
            "user": "default",
            "timestamp": int(time.time())
        }
        add_db_entry(entity)

    return redirect('/')

@app.post("/update-permissions/<filename>")
def update_permissions(filename):
    """Updates access permissions for a specific file."""
    new_users = request.form.get('users', '').split(',')
    new_users = [email.strip() for email in new_users if email.strip()]
    
    update_file_permissions(BUCKET_NAME, filename, new_users)
    
    # Update datastore entity
    query = datastore_client.query(kind='photos')
    query.add_filter('name', '=', filename)
    results = list(query.fetch(limit=1))
    
    if results:
        entity = results[0]
        entity['allowed_users'] = new_users
        datastore_client.put(entity)
    
    return redirect('/')

if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)