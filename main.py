import time
from flask import Flask, request

app = Flask(__name__)


@app.get("/")
def hello():
    """Return a friendly HTTP greeting."""
    who = request.args.get("who", default="World")
    time.sleep(5)
    return f"Hello {who}!\n"


if __name__ == "__main__":
    # Development only: run "python main.py" and open http://localhost:8080
    # When deploying to Cloud Run, a production-grade WSGI HTTP server,
    # such as Gunicorn, will serve the app.
    app.run(host="localhost", port=8080, debug=True)