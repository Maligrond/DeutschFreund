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

## Step 3: Frontend (Vercel) - The Easiest Way

1. **Commit & Push**: Make sure you have pushed all your latest code to GitHub first!
2. Go to **[vercel.com/new](https://vercel.com/new)**.
3. You should see your `deutschfreund` repository. Click **Import**.
4. **⚠️ CRITICAL STEP: Configure Project**
   - You will see a box that says **"Root Directory"**.
   - Click **Edit**.
   - Select the folder named **`frontend`** and click **Continue**.
   - *Why?* Because your website code lives inside the `frontend` folder, not at the top level.
5. **Framework Preset**:
   - Once you select the `frontend` folder, Vercel should automatically detect **Vite**.
   - If not, select **Vite** from the dropdown menu.
6. **Environment Variables** (Optional for now, but recommended):
   - Expand "Environment Variables".
   - Key: `VITE_API_URL`
   - Value: Your backend URL (e.g., `https://your-app.onrender.com`).
   - *Note: You can add this later in Settings if you don't have it yet.*
7. Click **Deploy**.
8. Wait ~1 minute. You should see fireworks! 🎆
   - If you see a 404 error, it usually means step 4 was skipped.

---

## Step 4: Final Config
1. Go back to Render -> Environment Variables.
2. Set `WEBAPP_URL` to your Vercel domain (`https://germanbuddy.vercel.app`).
3. Go to **BotFather** in Telegram.
4. Send `/newapp` -> Select bot -> Send Vercel URL.
5. In BotFather Menu Button config, also set the Vercel URL.

**Done!** 🎉
