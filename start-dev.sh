#!/bin/bash

# Скрипт для быстрого запуска в development режиме

echo "🚀 Starting GermanBuddy..."

# Функция для cleanup при выходе
cleanup() {
    echo "Stopping all processes..."
    kill $BOT_PID $API_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Проверяем что мы в корне проекта
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Запусти скрипт из корня проекта germanbuddy/"
    exit 1
fi

# Backend - Bot
echo "📱 Starting Telegram Bot..."
cd backend
source venv/bin/activate 2>/dev/null || python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -q
python -m bot.main &
BOT_PID=$!
cd ..

# Backend - API
echo "🔌 Starting API server..."
cd backend
uvicorn api.main:app --reload --port 8000 &
API_PID=$!
cd ..

# Frontend
echo "🎨 Starting Frontend..."
cd frontend
npm install -q
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ GermanBuddy запущен!"
echo ""
echo "📱 Bot: Telegram"
echo "🔌 API: http://localhost:8000/docs"
echo "🎨 Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"

# Ждём завершения
wait
