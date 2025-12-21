#!/bin/bash

# ============================================
# GermanBuddy - Один скрипт для всего
# ============================================

NGROK_DOMAIN="epirogenic-orthostichous-murray.ngrok-free.dev"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════╗"
echo "║      🇩🇪 GermanBuddy - One Click Start        ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# Cleanup при выходе и в начале
cleanup() {
    echo -e "\n${YELLOW}⏹ Останавливаем сервисы...${NC}"
    pkill -9 -f "uvicorn api.main:app" 2>/dev/null || true
    pkill -9 -f "python -m bot.main" 2>/dev/null || true
    pkill -9 -f "bot.main" 2>/dev/null || true
    pkill -9 -f "bot/main.py" 2>/dev/null || true
    pkill -9 -f "ngrok http" 2>/dev/null || true
    echo -e "${GREEN}✅ Всё остановлено${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Убиваем старые процессы
echo -e "${YELLOW}Останавливаем старые процессы...${NC}"
pkill -9 -f "uvicorn api.main:app" 2>/dev/null || true
pkill -9 -f "python -m bot.main" 2>/dev/null || true
pkill -9 -f "bot.main" 2>/dev/null || true
pkill -9 -f "bot/main.py" 2>/dev/null || true
pkill -9 -f "ngrok http" 2>/dev/null || true
sleep 1
sleep 1

# Проверяем директории
cd "$PROJECT_DIR" || exit 1

if [ ! -f "backend/.env" ]; then
    echo -e "${RED}❌ Создай файл backend/.env${NC}"
    echo "Скопируй backend/.env.example и заполни токены"
    exit 1
fi

# ============================================
# 1. Установка зависимостей Backend
# ============================================
echo -e "${BLUE}📦 Настроваем Backend...${NC}"

cd "$PROJECT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "Создаём виртуальное окружение..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null

echo -e "${GREEN}✅ Backend готов${NC}"

# ============================================
# 2. Сборка Frontend (опционально)
# ============================================
if [ -d "$PROJECT_DIR/frontend" ]; then
    echo -e "${BLUE}📦 Настроваем Frontend...${NC}"
    
    cd "$PROJECT_DIR/frontend"
    
    # Устанавливаем API URL
    echo "VITE_API_URL=https://${NGROK_DOMAIN}" > .env
    
    if [ ! -d "node_modules" ]; then
        echo "Устанавливаем npm зависимости..."
        npm install --silent 2>/dev/null
    fi
    
    # Собираем если нет dist
    if [ ! -d "dist" ]; then
        echo "Собираем frontend..."
        npm run build --silent 2>/dev/null
    fi
    
    echo -e "${GREEN}✅ Frontend готов${NC}"
fi

# ============================================
# 3. Запуск API
# ============================================
echo -e "${BLUE}🚀 Запускаем API...${NC}"

cd "$PROJECT_DIR/backend"
source venv/bin/activate

uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 2

if kill -0 $API_PID 2>/dev/null; then
    echo -e "${GREEN}✅ API запущен (PID: $API_PID)${NC}"
else
    echo -e "${RED}❌ API не запустился${NC}"
    exit 1
fi

# ============================================
# 4. Запуск Telegram бота
# ============================================
echo -e "${BLUE}🤖 Запускаем Telegram бот...${NC}"

cd "$PROJECT_DIR/backend"
source venv/bin/activate

python -m bot.main &
BOT_PID=$!
sleep 2

if kill -0 $BOT_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Бот запущен (PID: $BOT_PID)${NC}"
else
    echo -e "${RED}❌ Бот не запустился${NC}"
fi

# ============================================
# 5. Запуск ngrok
# ============================================
echo -e "${BLUE}🌐 Запускаем ngrok...${NC}"

ngrok http 8000 --domain=${NGROK_DOMAIN} > /dev/null 2>&1 &
NGROK_PID=$!
sleep 3

if kill -0 $NGROK_PID 2>/dev/null; then
    echo -e "${GREEN}✅ ngrok запущен${NC}"
else
    echo -e "${YELLOW}⚠️ ngrok не запустился (запусти вручную)${NC}"
fi

# ============================================
# Готово!
# ============================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 🎉 GermanBuddy запущен!                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🌐 Mini App:${NC}   https://${NGROK_DOMAIN}"
echo -e "${CYAN}📖 API Docs:${NC}   https://${NGROK_DOMAIN}/docs"
echo -e "${CYAN}📱 Локально:${NC}   http://localhost:8000"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Настройка в @BotFather:${NC}"
echo "  /mybots → Твой бот → Bot Settings → Menu Button"
echo -e "  URL: ${GREEN}https://${NGROK_DOMAIN}${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Нажми Ctrl+C для остановки${NC}"
echo ""

# Ждём
wait
