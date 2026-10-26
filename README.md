# Reelbox 📦

> Save reels & links on Telegram → AI auto-categorizes with takeaways → Browse in a private boxy dashboard.

An AI-powered smart bookmark manager built for Telegram. Forward any Instagram Reel, YouTube Short, or Web link, and Reelbox extracts thumbnails, key takeaways, categories, and tags—served in a private Notion-style dashboard with zero friction.

---

## ✨ Features

- 🤖 **Telegram First**: Forward any reel or link directly to `@ReelboxxBot`.
- 🧠 **Gemini AI Intelligence**: Auto-generates clean headlines, primary category, subcategories, tags, and bulleted key takeaways.
- 🖼️ **Instagram Reel Cover Proxy**: Extracts and displays authentic reel thumbnails with built-in proxy to prevent hotlink blocks.
- 🔐 **Private Magic Links**: Zero login forms. Each Telegram user receives an auto-generated private link (`/?token=...`) to view their own private vault.
- 🍱 **Boxy Grid UI**: Raindrop / Notion aesthetic card layout with instant click-to-reel redirect.
- ⚡ **Global Search (`Ctrl + K`)**: Instantly filter across all saved links, categories, and tags.
- 💰 **100% Free Tier Compatible**: Runs forever on free tiers of Telegram, Google AI Studio, and Render/Railway.

---

## 🚀 Quick Start (Local)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
APP_URL=http://localhost:8000
```
- **Telegram Bot Token**: Get free from [@BotFather](https://t.me/BotFather).
- **Gemini API Key**: Get free from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run Everything (1 Command)
```bash
python run.py
```
This starts both the **FastAPI Web Dashboard** (on port 8000) and the **Telegram Bot** polling simultaneously!

Visit `http://localhost:8000` in your browser, or send `/dashboard` to your Telegram bot.

---

## 🌐 Deploy to Cloud for Free (Render / Railway)

### Step 1: Push Code to GitHub

```bash
# 1. Initialize and add files
git add .

# 2. Commit
git commit -m "Initial commit of Reelbox"

# 3. Create a new repository on GitHub (Public or Private)
# 4. Link and push to GitHub:
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/reelbox.git
git push -u origin main
```
*(Your `.env` and `reelvault.db` are in `.gitignore` and will never be pushed).*

### Step 2: Deploy on Render.com (100% Free)

1. Sign up / Log in to [Render.com](https://render.com) (free).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository `reelbox`.
4. Configure service settings:
   - **Name**: `reelbox`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run.py`
   - **Instance Type**: `Free`
5. Under **Environment Variables**, add:
   - `TELEGRAM_BOT_TOKEN` = `your_bot_token_from_botfather`
   - `GEMINI_API_KEY` = `your_gemini_api_key`
   - `APP_URL` = `https://reelbox-xxxx.onrender.com` *(use the Render assigned URL)*
6. Click **Deploy Web Service**!

Render will build and deploy your app in 2 minutes. Once live, every user who runs `/dashboard` in Telegram will get their private public URL with an inline button!

---

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome and quick instructions |
| `/dashboard` | Get your personalized private magic link to the web vault |
| `/categories` | Interactive category selector |
| `/recent` | List 5 most recently saved reels |
| `/search <query>` | Search your reels by keyword |
| `/browse <Category>` | Filter by specific category |
| `/stats` | View total reels saved and category counts |
| `/delete <id>` | Delete a saved reel by ID |
| `/help` | Complete commands list |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **AI Engine**: Google GenAI SDK (`gemini-3.5-flash`)
- **Telegram**: `python-telegram-bot` (Async polling)
- **Database**: SQLite with `aiosqlite`
- **Frontend**: Responsive Boxy Grid UI (HTML5, Vanilla JS, CSS3)
