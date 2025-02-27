import time
import os
import traceback
from flask import Flask, request, render_template, redirect, make_response, url_for
from werkzeug.utils import secure_filename
import storage
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Print environment variables for debugging
print("Environment variables:")
print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"GCS_BUCKET_NAME: {os.getenv('GCS_BUCKET_NAME')}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
print(f"LOCAL_DEVELOPMENT: {os.getenv('LOCAL_DEVELOPMENT')}")

# Set up logging with basic configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit uploads to 16MB
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "your-bucket-name")
print(f"Using bucket: {BUCKET_NAME}")

# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    return "File not found", 404

@app.errorhandler(500)
def server_error(e):
    return "An internal server error occurred", 500

@app.get("/")
def index():
    """Fetches and displays uploaded photos."""
    try:
        print("Trying to query photos from Datastore...")
        query = storage.datastore_client.query(kind='photos')
        photos = list(query.fetch())
        print(f"Found {len(photos)} photos")
        
        # Generate API URLs for each photo
        for photo in photos:
            if 'name' in photo:
                photo['image_url'] = url_for('get_image', filename=photo['name'])
        
        return render_template('index.html', photos=photos)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        logger.error(f"Error in index route: {str(e)}")
        return redirect(url_for('error_page', error_code=500))

@app.get("/images/<filename>")
def get_image(filename):
    """Streams an image file from Google Cloud Storage."""
    try:
        print(f"Image request for: {filename}")
        
        # Get file content from GCS
        file_bytes = storage.get_file_stream(BUCKET_NAME, filename)
        
        # Determine content type
        content_type = storage.get_content_type(filename)
        print(f"Serving image with content type: {content_type}")
        
        # Create a response with the file content
        response = make_response(file_bytes)
        response.headers.set('Content-Type', content_type)
        response.headers.set('Cache-Control', 'public, max-age=3600')
        
        return response
    except FileNotFoundError:
        print(f"Image not found: {filename}")
        logger.warning(f"Image not found")
        return redirect(url_for('error_page', error_code=404))
    except Exception as e:
        print(f"Error retrieving image: {str(e)}")
        traceback.print_exc()
        logger.error(f"Error retrieving image")
        return redirect(url_for('error_page', error_code=500))

@app.post("/upload")
def upload_image():
    """Handles image uploads and stores metadata."""
    try:
        print("Processing upload request")
        if 'file' not in request.files:
            print("No file part in request")
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            print("No file selected")
            return redirect(url_for('index'))
        
        if file:
            filename = secure_filename(file.filename)
            print(f"Processing upload for file: {filename}")
            # Set file position to start
            file.seek(0)
            
            storage.upload_file(BUCKET_NAME, file, filename)
            print(f"File uploaded successfully")
            
            entity = {
                "name": filename,
                "user": "default",
                "timestamp": int(time.time())
            }
            storage.add_db_entry(entity)
            print(f"Database entry added")
        
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Upload error: {str(e)}")
        traceback.print_exc()
        logger.error(f"Error in upload")
        return redirect(url_for('error_page', error_code=500))

@app.post("/delete")
def delete_image():
    """Handles image deletion."""
    try:
        filename = request.form.get("filename")
        if filename:
            print(f"Deleting file: {filename}")
            storage.delete_file(BUCKET_NAME, filename)
            print(f"File deleted successfully")
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Delete error: {str(e)}")
        traceback.print_exc()
        logger.error(f"Error in delete")
        return redirect(url_for('error_page', error_code=500))

@app.route('/error/<int:error_code>')
def error_page(error_code):
    """Generic error page that doesn't leak information"""
    error_messages = {
        404: "The requested resource was not found.",
        500: "An internal server error occurred.",
        403: "You don't have permission to access this resource."
    }
    message = error_messages.get(error_code, "An error occurred.")
    try:
        return render_template('error.html', error_code=error_code, message=message), error_code
    except Exception as e:
        print(f"Error rendering error page: {str(e)}")
        traceback.print_exc()
        return f"Error {error_code}: {message}", error_code

# Debug endpoint to check environment and connections
@app.route('/debug')
def debug_info():
    """Returns debug information about the environment"""
    debug_data = {
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "GCS_BUCKET_NAME": os.getenv("GCS_BUCKET_NAME"),
        "LOCAL_DEVELOPMENT": os.getenv("LOCAL_DEVELOPMENT"),
        "BUCKET_NAME": BUCKET_NAME,
    }
    # Try to access the bucket to check permissions
    try:
        bucket = storage.storage_client.bucket(BUCKET_NAME)
        blobs = list(bucket.list_blobs(max_results=5))
        debug_data["bucket_accessible"] = True
        debug_data["blob_count"] = len(blobs)
        debug_data["sample_blobs"] = [b.name for b in blobs]
    except Exception as e:
        debug_data["bucket_accessible"] = False
        debug_data["error"] = str(e)
    
    return debug_data

