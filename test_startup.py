
import os
import sys
from pathlib import Path

# Add backend to sys.path, similar to PYTHONPATH="backend"
backend_path = Path.cwd() / "backend"
sys.path.append(str(backend_path))

# Mock Environment Variables
os.environ["TELEGRAM_TOKEN"] = "mock_token"
os.environ["GOOGLE_API_KEY"] = "mock_key"
os.environ["DATABASE_URL"] = "postgres://user:pass@host/db" # Mock Neon URL

print(f"Testing import with PYTHONPATH={sys.path[-1]}")

try:
    # Try importing the entrypoint
    from api.index import application
    print("✅ Success! Application imported successfully.")
except Exception as e:
    print(f"❌ Failed to start: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
