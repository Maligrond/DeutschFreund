## Step 3: Deploy to Vercel (Frontend + Backend)

1. **Commit & Push**: Push your changes to GitHub (`git push`).
2. Go to **[vercel.com](https://vercel.com)** -> Add New Project -> Import `deutschfreund`.
3. **Project Settings**:
   - **Root Directory**: Leave it empty (`./`). **Do NOT select 'frontend' anymore.**
   - *Why?* We are now deploying the whole app (Backend + Frontend) together!
4. **Environment Variables**:
   Add the following variables (you can get them from Neon.tech and Telegram):
   - `DATABASE_URL`: `postgresql+asyncpg://...` (From Neon, change `postgres://` to `postgresql+asyncpg://`)
   - `TELEGRAM_TOKEN`: Your Bot Token from BotFather.
   - `WEBHOOK_SECRET`: A random string (e.g., `mysecret123`).
   - `GOOGLE_API_KEY`: Your Gemini API Key.
5. Click **Deploy**.

---

## Step 4: Final Setup (Webhook)

Since Vercel puts the bot to sleep when not used, we can't use "Polling". We must use **Webhooks**.

1. Wait for deployment to finish. Copy your Vercel Domain (e.g., `https://deutschfreund.vercel.app`).
2. Open your browser and visit this URL to set the webhook:
   ```
   https://YOUR_DOMAIN.vercel.app/api/webhook/set?url=https://YOUR_DOMAIN.vercel.app/api/webhook/telegram
   ```
3. You should see `{"status":"ok", ...}`.
4. **Done!** Your bot is now live on Vercel.

> **Note**: The frontend will be at `https://deutschfreund.vercel.app` and the API at `https://deutschfreund.vercel.app/api/...`.

