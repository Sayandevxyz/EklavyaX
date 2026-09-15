import sys
import os

# Add backend to sys.path
cur_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(cur_dir, "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

# Handler export for Vercel Serverless
handler = app
