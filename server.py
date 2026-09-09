"""
InterviewIQ – waitress server entry point
Starts the production WSGI server on port 5000
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from waitress import serve
from app import app

PORT = int(os.getenv("PORT", 5000))

if __name__ == "__main__":
    print(f"[InterviewIQ] Waitress server starting on http://0.0.0.0:{PORT}", flush=True)
    serve(app, host="0.0.0.0", port=PORT, threads=4)
