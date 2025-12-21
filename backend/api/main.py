"""
FastAPI приложение для Telegram Mini App.
Включает API endpoints и раздачу статики frontend.
"""

import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from database.db import init_db, close_db
from .routes import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Путь к frontend dist
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle events для FastAPI."""
    # Startup
    logger.info("Starting GermanBuddy API...")
    await init_db()
    logger.info("Database initialized")
    
    # Инициализируем Gemini клиент для API (переводы)
    from config import settings
    from bot.gemini_client import init_gemini_client
    try:
        init_gemini_client(settings.google_api_key)
        logger.info("Gemini client initialized for API")
    except Exception as e:
        logger.warning(f"Failed to init Gemini client: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GermanBuddy API...")
    await close_db()
    logger.info("Database connection closed")


# Создание приложения
app = FastAPI(
    title="GermanBuddy API",
    description="API для Telegram Mini App изучения немецкого языка.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS Middleware для Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# No-Cache Middleware для Telegram Mini App (обходит агрессивное кэширование)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        
        # Для HTML и JS файлов отключаем кэширование
        path = request.url.path
        is_static = path.startswith('/assets') or path.startswith('/vite.svg')
        is_api = path.startswith('/api') or path.startswith('/docs') or path.startswith('/redoc')
        
        # Если это не статика и не API (значит, это HTML/SPA/JS), отключаем кэш
        if not is_static and not is_api:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response

app.add_middleware(NoCacheMiddleware)


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Обработка непредвиденных ошибок."""
    logger.error("Unhandled error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }
    )


# Подключение API роутеров
# Подключение API роутеров
app.include_router(router, prefix="/api")

# Webhook router for Vercel
from .webhook import router as webhook_router
app.include_router(webhook_router, prefix="/api")



# ============ SYSTEM ENDPOINTS ============

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "germanbuddy-api",
        "version": "1.0.0",
    }


# ============ FRONTEND STATIC FILES ============

# Монтируем статику если frontend собран
if FRONTEND_DIR.exists():
    # Assets (js, css, images)
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # Статические файлы в корне (favicon, etc)
    @app.get("/vite.svg", include_in_schema=False)
    async def vite_svg():
        svg_path = FRONTEND_DIR / "vite.svg"
        if svg_path.exists():
            return FileResponse(svg_path)
        return JSONResponse({"error": "Not found"}, status_code=404)


# SPA Fallback - отдаём index.html для всех несуществующих путей
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve Vue SPA - fallback to index.html."""
    
    # Пропускаем API запросы
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    # Если frontend не собран - показываем инструкцию
    if not FRONTEND_DIR.exists():
        return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GermanBuddy</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            text-align: center;
            max-width: 400px;
        }}
        h1 {{ font-size: 48px; margin-bottom: 20px; }}
        p {{ color: var(--tg-theme-hint-color, #999); margin-bottom: 10px; }}
        code {{
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
        }}
        .btn {{
            display: inline-block;
            margin-top: 20px;
            padding: 12px 24px;
            background: var(--tg-theme-button-color, #3390ec);
            color: var(--tg-theme-button-text-color, #fff);
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🇩🇪</h1>
        <h2>GermanBuddy</h2>
        <p style="margin-top: 20px;">Frontend ещё не собран.</p>
        <p>Запусти в папке frontend:</p>
        <p><code>npm run build</code></p>
        <a href="/docs" class="btn">API Docs →</a>
    </div>
    <script>
        if (window.Telegram?.WebApp) {{
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();
        }}
    </script>
</body>
</html>
        """, status_code=200)
    
    # Проверяем есть ли запрашиваемый файл
    file_path = FRONTEND_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # SPA fallback - отдаём index.html
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    return JSONResponse({"error": "Not found"}, status_code=404)
