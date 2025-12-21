# GermanBuddy 🇩🇪

**AI Языковой Друг** — Telegram бот + Mini App для изучения немецкого языка через общение с искусственным интеллектом.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Vue](https://img.shields.io/badge/Vue-3.4+-green?logo=vue.js)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-blue?logo=telegram)

---

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| 💬 **AI Чат** | Практика немецкого через общение с Gemini AI |
| 🔔 **Proactive Messages** | Бот пишет первым, если ты забыл попрактиковаться |
| 📊 **Статистика** | Отслеживание прогресса в Mini App |
| 🔥 **Streak** | Мотивация через серию дней подряд |
| 📚 **Словарь** | Автоматическое сохранение новых слов |
| 🎯 **Персонализация** | Настройка уровня, цели и стиля общения |
| 🎭 **Личности бота** | Дружелюбный / Строгий / Романтичный |

---

## 🏗 Структура проекта

```
germanbuddy/
├── backend/
│   ├── bot/
│   │   ├── main.py           # Точка входа бота
│   │   ├── handlers.py       # Обработчики команд
│   │   ├── gemini_client.py  # Интеграция с Gemini AI
│   │   └── scheduler.py      # Proactive сообщения
│   ├── api/
│   │   ├── main.py           # FastAPI приложение
│   │   ├── routes.py         # API endpoints
│   │   └── models.py         # Pydantic модели
│   ├── database/
│   │   ├── db.py             # Подключение к PostgreSQL
│   │   └── models.py         # SQLAlchemy модели
│   ├── config.py             # Конфигурация
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── views/            # Stats, Settings, History
│   │   ├── composables/      # useTelegram, useApi
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
└── README.md
```

---

## 🚀 Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/your-repo/germanbuddy.git
cd germanbuddy
```

### 2. Настройка переменных окружения

```bash
cp backend/.env.example backend/.env
```

Отредактируй `backend/.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:AABBccDDeeFFgg...
GOOGLE_API_KEY=AIzaSy...
DATABASE_URL=postgresql://user:password@localhost:5432/germanbuddy
REDIS_URL=redis://localhost:6379
API_BASE_URL=https://your-domain.com
```

### 3. Запуск через Docker (рекомендуется)

```bash
docker-compose up -d
```

### 4. Или запуск вручную

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1: Бот
python -m bot.main

# Terminal 2: API
uvicorn api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Получение токенов

### Telegram Bot Token

1. Открой [@BotFather](https://t.me/BotFather)
2. Отправь `/newbot`
3. Следуй инструкциям
4. Скопируй токен

### Google API Key

1. Открой [Google AI Studio](https://aistudio.google.com/apikey)
2. Создай API Key
3. Скопируй ключ

---

## 📱 Настройка Mini App

1. Открой [@BotFather](https://t.me/BotFather)
2. Выбери своего бота
3. `/mybots` → Твой бот → Bot Settings → Menu Button
4. Установи URL: `https://your-frontend-domain.com`

---

## 🔌 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/user/{id}/stats` | Статистика пользователя |
| GET | `/api/user/{id}/history` | История сообщений |
| GET | `/api/user/{id}/vocabulary` | Словарь слов |
| GET | `/api/user/{id}/settings` | Настройки |
| PUT | `/api/user/{id}/settings` | Обновить настройки |
| GET | `/health` | Health check |

📖 **Swagger UI:** http://localhost:8000/docs

---

## 🚢 Деплой

### Backend (Railway/Render)

1. Подключи GitHub репозиторий
2. Укажи `backend` как root directory
3. Добавь переменные окружения
4. Deploy!

### Frontend (Vercel/Netlify)

1. Подключи GitHub репозиторий
2. Укажи `frontend` как root directory
3. Build command: `npm run build`
4. Output directory: `dist`

### База данных

- **Supabase** — бесплатный PostgreSQL
- **Railway** — managed PostgreSQL
- **Neon** — serverless PostgreSQL

---

## 🐳 Docker

### Только база данных

```bash
docker-compose up postgres redis -d
```

### Полный стек

```bash
docker-compose up -d
```

---

## 🧪 TODO

- [ ] 🎙️ Голосовые сообщения (Speech-to-Text)
- [ ] 🔗 Webhook вместо polling
- [ ] ✅ Unit и интеграционные тесты
- [ ] 🔄 CI/CD pipeline
- [ ] 📝 Система упражнений
- [ ] 🏆 Достижения и награды

---

## 🛠 Технологии

**Backend:**
- Python 3.11+
- aiogram 3.x (Telegram Bot API)
- FastAPI (REST API)
- SQLAlchemy 2.0 + asyncpg
- Google Gemini AI
- APScheduler (cron jobs)
- Redis (кеширование)

**Frontend:**
- Vue 3 + Composition API
- TypeScript
- Vite
- Tailwind CSS
- Chart.js
- Telegram WebApp SDK

---

## 📄 Лицензия

MIT License © 2024

---

**Made with ❤️ for German learners**
