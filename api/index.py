from backend.api.main import app
import os
import sys

# Add backend to sys.path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

# Vercel expects 'app' or 'application'
application = app
