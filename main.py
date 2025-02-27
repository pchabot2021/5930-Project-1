import time
import os
import json
import traceback
from flask import Flask, request, render_template, redirect, make_response, url_for
from werkzeug.utils import secure_filename
import storage
import logging

# Try to load dotenv for local development, but don't fail in production
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("Running without dotenv (likely in production)")
    pass

# Set up logging with basic configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "your-bucket-name")
print(f"Using project: {PROJECT_ID}, bucket: {BUCKET_NAME}")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit uploads to 16MB

# Simple health check endpoint
@app.route('/health')
def health_check():
    """Simple health check to verify the app is running"""
    return "OK", 200

# Custom error handlerss
@app.errorhandler(404)
def page_not_found(e):
    return "File not found", 404

@app.errorhandler(500)
def server_error(e):
    return "An internal server error occurred", 500

@app.get("/")
def index():
    """Fetches and displays uploaded photos with their metadata."""
    try:
        query = storage.datastore_client.query(kind='photos')
        photos = list(query.fetch())
        
        if not photos:
            logger.info("No photos found in database")
            return render_template('index.html', photos=[])
        
        # Generate API URLs for each photo and get metadata
        for photo in photos:
            if 'name' in photo:
                photo['image_url'] = url_for('get_image', filename=photo['name'])
                
                # Try get metadata
                try:
                    base_name = os.path.splitext(photo['name'])[0]
                    json_filename = f"{base_name}.json"
                    
                    metadata = storage.get_metadata(BUCKET_NAME, json_filename)
                    if metadata:
                        photo['title'] = metadata.get('title', 'No title available')
                        photo['description'] = metadata.get('description', 'No description available')
                    else:
                        photo['title'] = photo['name']
                        photo['description'] = 'No description available'
                except Exception as e:
                    logger.error(f"Error getting metadata for {photo['name']}: {str(e)}")
                    photo['title'] = photo['name']
                    photo['description'] = 'Could not load description'
        
        return render_template('index.html', photos=photos)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('error_page', error_code=500))

@app.get("/images/<filename>")
def get_image(filename):
    """Streams an image file from Google Cloud Storage."""
    try:
        # Get file content from GCS
        file_bytes = storage.get_file_stream(BUCKET_NAME, filename)
        
        # Determine content type
        content_type = storage.get_content_type(filename)
        
        # Create a response with the file content
        response = make_response(file_bytes)
        response.headers.set('Content-Type', content_type)
        response.headers.set('Cache-Control', 'public, max-age=3600')
        
        return response
    except FileNotFoundError:
        logger.warning(f"Image not found: {filename}")
        return redirect(url_for('error_page', error_code=404))
    except Exception as e:
        logger.error(f"Error retrieving image: {str(e)}")
        return redirect(url_for('error_page', error_code=500))

@app.post("/upload")
def upload_image():
    """Handles image uploads and stores metadata."""
    try:
        if 'file' not in request.files:
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            return redirect(url_for('index'))
        
        if file:
            filename = secure_filename(file.filename)
    
            file.seek(0)
            
            storage.upload_file(BUCKET_NAME, file, filename)
            
            entity = {
                "name": filename,
                "user": "default",
                "timestamp": int(time.time())
            }
            storage.add_db_entry(entity)
        
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('error_page', error_code=500))

@app.post("/delete")
def delete_image():
    """Handles image deletion."""
    try:
        filename = request.form.get("filename")
        if filename:
            storage.delete_file(BUCKET_NAME, filename)
            
            # Also delete the metadata JSON file if it exists
            try:
                base_name = os.path.splitext(filename)[0]
                json_filename = f"{base_name}.json"
                storage.delete_file_without_db(BUCKET_NAME, json_filename)
            except Exception as e:
                logger.warning(f"Could not delete metadata file: {str(e)}")
                
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in delete: {str(e)}")
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
        return f"Error {error_code}: {message}", error_code

# Debug endpoint to check environment and connections
@app.route('/debug')
def debug_info():
    """Returns debug information about the environment"""
    debug_data = {
        "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "GCS_BUCKET_NAME": os.getenv("GCS_BUCKET_NAME"),
        "GEMINI_API_SET": "Yes" if os.getenv("GEMINI_API") else "No",
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 for Cloud Run
    print(f"Starting development server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)