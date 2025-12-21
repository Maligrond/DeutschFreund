import sys
import os

# Add the 'backend' folder to the system path so we can import from it
# Vercel's root is the repository root
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

# Import the FastAPI app
# We need to make sure the database connection handles missing variables nicely
# ensuring the app loads even if config is partial.
try:
    from api.main import app
    application = app
except Exception as e:
    import traceback
    # Fallback: Raw ASGI app to show errors 
    async def application(scope, receive, send):
        status_text = f"Startup Error:\n{str(e)}\n\n{traceback.format_exc()}"
        await send({'type': 'http.response.start', 'status': 500, 'headers': [[b'content-type', b'text/plain']]})
        await send({'type': 'http.response.body', 'body': status_text.encode('utf-8')})
