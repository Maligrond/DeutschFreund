# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
# libpq-dev нужен для установки psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения (папка bot, api, database, etc.)
COPY . .

# Открываем порт для FastAPI
EXPOSE 8000

# Команда запуска (по умолчанию запускает start.py который есть в корне backend или аналогичный)
# В нашем случае мы запускаем uvicorn для API и бот отдельно или вместе.
# Лучше запускать через скрипт-обертку, но для простоты запустим API, 
# а бот должен быть запущен как фоновая задача или отдельный worker.
# В Render на free tier лучше запускать всё в одном процессе.

CMD ["sh", "-c", "python3 -m bot.main & uvicorn api.main:app --host 0.0.0.0 --port 8000"]
