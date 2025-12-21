# 🚀 Free Hosting Guide for GermanBuddy

Here is how to host your app completely for free using modern cloud providers.

## Stack Overview
- **Database**: **Neon.tech** (Free Serverless PostgreSQL).
- **Backend (API + Bot)**: **Render.com** (Free Web Service).
- **Frontend**: **Vercel** (Free Static Hosting).

---

## Step 1: Database (Neon.tech)
1. Go to [neon.tech](https://neon.tech) and sign up.
2. Create a new project.
3. Copy the **ConnectionString** (Postgres URL). It looks like `postgres://user:pass@ep-xyz.aws.neon.tech/neondb`.
   > ⚠️ **Important**: For Python/SQLAlchemy, you need to change `postgres://` to `postgresql+asyncpg://` in the URL later.

---

## Step 2: Backend (Render.com)
1. Push your code to a **GitHub repository**.
2. Go to [render.com](https://render.com) -> New **Web Service**.
3. Connect your GitHub repo.
4. Settings:
   - **Root Directory**: `backend` (this is important!)
   - **Runtime**: Docker
   - **Instance Type**: Free
   - **Environment Variables**:
     - `DATABASE_URL`: Your Neon URL (change `postgres://` to `postgresql+asyncpg://`).
     - `TELEGRAM_TOKEN`: Your bot token.
     - `GEMINI_API_KEY`: Your key.
     - `WEBAPP_URL`: *You will fill this later after Frontend deploy.*
5. Click **Create Web Service**.

---

## Step 3: Frontend (Vercel)
1. Go to [vercel.com](https://vercel.com) -> Add New Project.
2. Import the same GitHub repo.
3. Settings:
   - **Root Directory**: `frontend` (Edit -> select `frontend` folder).
   - **Framework Preset**: Vite (should contain `npm run build`).
4. **Environment Variables**:
   - `VITE_API_URL`: The URL of your Render backend (e.g., `https://germanbuddy.onrender.com`).
5. Click **Deploy**.
6. Copy the resulting domain (e.g., `https://germanbuddy.vercel.app`).

---

## Step 4: Final Config
1. Go back to Render -> Environment Variables.
2. Set `WEBAPP_URL` to your Vercel domain (`https://germanbuddy.vercel.app`).
3. Go to **BotFather** in Telegram.
4. Send `/newapp` -> Select bot -> Send Vercel URL.
5. In BotFather Menu Button config, also set the Vercel URL.

**Done!** 🎉
