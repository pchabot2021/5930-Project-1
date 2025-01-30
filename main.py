#main.py
import time
from flask import Flask, request, render_template, redirect
from werkzeug.utils import secure_filename
import storage

app = Flask(__name__)
BUCKET_NAME = "chabotproject1bucket"

@app.get("/")
def index():
    """Fetches and displays uploaded photos."""
    query = storage.datastore_client.query(kind='photos')
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
        public_url = storage.upload_file(BUCKET_NAME, file, filename)
        
        entity = {
            "name": filename,
            "url": public_url,
            "user": "default",
            "timestamp": int(time.time())
        }
        storage.add_db_entry(entity)
    
    return redirect('/')

@app.post("/delete")
def delete_image():
    """Handles image deletion."""
    filename = request.form.get("filename")
    if filename:
        storage.delete_file(BUCKET_NAME, filename)
    return redirect('/')

if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)