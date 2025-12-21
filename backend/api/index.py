try:
    from api.main import app
    application = app
except Exception as e:
    import traceback
    # Fallback: Raw ASGI app (no external dependencies)
    async def application(scope, receive, send):
        status_text = f"CRITICAL STARTUP ERROR\n\n{str(e)}\n\n{traceback.format_exc()}"
        
        await send({
            'type': 'http.response.start',
            'status': 500,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': status_text.encode('utf-8'),
        })
