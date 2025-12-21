try:
    from api.main import app
    application = app
except Exception as e:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    
    # Fallback app to show the error
    application = FastAPI()
    
    @application.route("/{path:path}")
    async def catch_all(scope, receive, send):
        # We use a low-level approach to ensure we can reply even if high-level stuff breaks
        error_msg = f"⚠️ CRITICAL STARTUP ERROR ⚠️\n\n{str(e)}\n\n{traceback.format_exc()}"
        response = PlainTextResponse(error_msg, status_code=500)
        await response(scope, receive, send)
