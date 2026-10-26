"""
Reelbox - Telegram Bot
The main entry point for users to save and retrieve reels.
"""

import os
import json
import logging
import html
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from database import (
    init_db, upsert_user, save_reel, get_reels_by_user,
    get_categories_by_user, get_reel_count, delete_reel,
    get_or_create_vault_token
)
from extractor import extract_url_from_text, extract_metadata
from categorizer import categorize_reel

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

APP_URL = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Emoji mapping for categories ──
CATEGORY_EMOJI = {
    "design": "🎨",
    "tech & ai": "🤖",
    "movies & shows": "🎬",
    "food & cooking": "🍳",
    "music": "🎵",
    "fitness & health": "💪",
    "travel": "✈️",
    "business & finance": "💼",
    "education": "📚",
    "fashion & beauty": "👗",
    "humor & memes": "😂",
    "motivation & self-help": "🚀",
    "photography & videography": "📷",
    "tools & apps": "🔧",
    "other": "📌",
    "uncategorized": "❓",
}


def get_emoji(category: str) -> str:
    return CATEGORY_EMOJI.get(category.lower(), "📌")


# ── Command Handlers ──

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    welcome = (
        f"👋 Hey {user.first_name}! Welcome to **Reelbox**\n\n"
        "I help you organize reels & links you save — so you actually find them later.\n\n"
        "**How to use:**\n"
        "📎 Send me any reel/video link → I'll categorize & save it\n"
        "📂 /categories → See your saved categories\n"
        "🔍 /search `keyword` → Find a saved reel\n"
        "📊 /stats → Your vault stats\n"
        "📋 /recent → Last 5 saved reels\n\n"
        "**Supported platforms:**\n"
        "Instagram • YouTube • Twitter/X • TikTok • Reddit • Any URL\n\n"
        "Try it now — send me a reel link! 🚀"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📖 **Reelbox Commands**\n\n"
        "📎 **Send a link** → Auto-categorize & save\n"
        "📂 /categories → View all your categories\n"
        "📋 /recent → Last 5 saved reels\n"
        "🔍 /search `keyword` → Search your reels\n"
        "📊 /stats → Your vault statistics\n"
        "🏷️ /browse `category` → Browse reels in a category\n"
        "🗑️ /delete `id` → Delete a saved reel\n"
        "❓ /help → Show this message\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    user_id = update.effective_user.id
    count = await get_reel_count(user_id)
    categories = await get_categories_by_user(user_id)

    if count == 0:
        await update.message.reply_text(
            "📊 Your vault is empty!\nSend me a reel link to get started. 🚀"
        )
        return

    stats_text = f"📊 **Your Reelbox Stats**\n\n"
    stats_text += f"📎 Total saved: **{count}** reels\n"
    stats_text += f"📂 Categories: **{len(categories)}**\n\n"

    for cat in categories:
        emoji = get_emoji(cat["category"])
        stats_text += f"{emoji} {cat['category']}: {cat['count']}\n"

    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /categories command — show categories as buttons."""
    user_id = update.effective_user.id
    categories = await get_categories_by_user(user_id)

    if not categories:
        await update.message.reply_text("📂 No categories yet. Send me a link to start!")
        return

    keyboard = []
    for cat in categories:
        emoji = get_emoji(cat["category"])
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {cat['category']} ({cat['count']})",
                callback_data=f"cat:{cat['category']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📂 **Your Categories:**\n\nTap to browse:", reply_markup=reply_markup, parse_mode="Markdown")


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard and /web command with private magic link."""
    user = update.effective_user
    count = await get_reel_count(user.id)
    token = await get_or_create_vault_token(user.id)
    magic_url = f"{APP_URL}/?token={token}"

    safe_name = html.escape(user.first_name or "Friend")
    text = (
        f"🔐 <b>Your Private Reelbox Dashboard</b>\n\n"
        f"Hey {safe_name}, here is your private link. It opens your personal vault with <b>{count}</b> saved bookmarks:\n\n"
        f"👉 <a href=\"{magic_url}\">Open My Private Vault</a>\n\n"
        f"🔗 <b>Direct Link:</b>\n<code>{magic_url}</code>\n\n"
        f"🔒 <i>This is your private link. Keep it secret or bookmark it on your computer.</i>"
    )

    # Telegram API rejects localhost/127.0.0.1 inside inline keyboard buttons
    is_local = "localhost" in magic_url or "127.0.0.1" in magic_url
    if not is_local and magic_url.startswith("http"):
        keyboard = [[InlineKeyboardButton("🚀 Open Private Vault", url=magic_url)]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recent command."""
    user_id = update.effective_user.id
    reels = await get_reels_by_user(user_id, limit=5)

    if not reels:
        await update.message.reply_text("📋 No reels saved yet! Send me a link.")
        return

    text = "📋 **Recent Reels:**\n\n"
    for r in reels:
        emoji = get_emoji(r["category"])
        tags = json.loads(r["tags"]) if r["tags"] else []
        tag_str = " ".join(f"#{t.replace(' ', '_')}" for t in tags[:3])
        text += f"{emoji} **{r['category']}** → {r['subcategory'] or 'General'}\n"
        text += f"📝 {r['summary'][:100]}\n"
        text += f"🔗 [Open Reel]({r['url']})\n"
        if tag_str:
            text += f"🏷️ {tag_str}\n"
        text += f"🆔 `#{r['id']}` | 🕐 {r['created_at'][:10]}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search keyword command."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("🔍 Usage: `/search design tips`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    reels = await get_reels_by_user(user_id, search=query, limit=10)

    if not reels:
        await update.message.reply_text(f"🔍 No results for \"{query}\". Try different keywords!")
        return

    text = f"🔍 **Results for \"{query}\":**\n\n"
    for r in reels:
        emoji = get_emoji(r["category"])
        text += f"{emoji} **{r['category']}** → {r['subcategory'] or 'General'}\n"
        text += f"📝 {r['summary'][:100]}\n"
        text += f"🔗 [Open]({r['url']}) | 🆔 `#{r['id']}`\n\n"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def browse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /browse category command."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("🏷️ Usage: `/browse Design`\nUse /categories to see your categories.", parse_mode="Markdown")
        return

    category = " ".join(context.args)
    reels = await get_reels_by_user(user_id, category=category, limit=10)

    if not reels:
        await update.message.reply_text(f"📂 No reels found in \"{category}\".")
        return

    emoji = get_emoji(category)
    text = f"{emoji} **{category}** ({len(reels)} reels):\n\n"
    for r in reels:
        text += f"• {r['summary'][:80]}\n"
        text += f"  🔗 [Open]({r['url']}) | 🆔 `#{r['id']}`\n\n"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delete id command."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("🗑️ Usage: `/delete 42`", parse_mode="Markdown")
        return

    try:
        reel_id = int(context.args[0].lstrip('#'))
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Use a number like `/delete 42`", parse_mode="Markdown")
        return

    deleted = await delete_reel(user_id, reel_id)
    if deleted:
        await update.message.reply_text(f"✅ Reel #{reel_id} deleted!")
    else:
        await update.message.reply_text(f"❌ Reel #{reel_id} not found in your vault.")


# ── Callback Query Handler (for category buttons) ──

async def category_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category button taps."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("cat:"):
        category = data[4:]
        user_id = query.from_user.id
        reels = await get_reels_by_user(user_id, category=category, limit=10)

        if not reels:
            await query.edit_message_text(f"📂 No reels in \"{category}\".")
            return

        emoji = get_emoji(category)
        text = f"{emoji} **{category}** ({len(reels)} reels):\n\n"
        for r in reels:
            text += f"• {r['summary'][:80]}\n"
            text += f"  🔗 [Open]({r['url']}) | 🆔 `#{r['id']}`\n\n"

        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)


# ── Main Message Handler (processes links) ──

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message — look for URLs to process."""
    text = update.message.text
    user = update.effective_user

    # Ensure user exists in DB
    await upsert_user(user.id, user.username, user.first_name)

    # Try to extract a URL and any user notes
    url, user_notes = extract_url_from_text(text)

    if not url:
        await update.message.reply_text(
            "🤔 I didn't find a link in your message.\n"
            "Send me a reel or video link and I'll categorize it for you!\n\n"
            "Type /help for commands."
        )
        return

    # Processing indicator
    processing_msg = await update.message.reply_text("⏳ Processing your link...")

    try:
        # Step 1: Extract metadata
        metadata = await extract_metadata(url)
        metadata["user_notes"] = user_notes

        # Step 2: AI categorization
        ai_result = await categorize_reel(metadata)

        # Step 3: Merge data
        reel_data = {**metadata, **ai_result}

        # Step 4: Save to database
        reel_id = await save_reel(user.id, reel_data)

        if reel_id == -1:
            await processing_msg.edit_text("⚠️ You've already saved this reel!")
            return

        # Step 5: Send confirmation
        emoji = get_emoji(ai_result["category"])
        tags = " ".join(f"#{t.replace(' ', '_')}" for t in ai_result.get("tags", []))
        key_points = ai_result.get("key_points", [])
        points_text = "\n".join(f"  • {p}" for p in key_points) if key_points else "  No key points extracted"

        result_text = (
            f"✅ **Saved to Reelbox!** (#{reel_id})\n\n"
            f"{emoji} **Category:** {ai_result['category']}\n"
            f"📁 **Subcategory:** {ai_result.get('subcategory', 'General')}\n"
            f"🏷️ **Tags:** {tags}\n\n"
            f"📝 **Summary:**\n{ai_result.get('summary', 'N/A')}\n\n"
            f"💡 **Key Points:**\n{points_text}\n\n"
            f"🔗 [Open Original]({url})"
        )

        await processing_msg.edit_text(result_text, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ Oops, something went wrong processing that link.\n"
            f"Error: {str(e)[:200]}\n\n"
            f"Please try again or try a different link."
        )


# ── Main ──

async def post_init(application: Application):
    """Initialize database on startup."""
    await init_db()
    logger.info("Database initialized!")


def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("ERROR: Please set TELEGRAM_BOT_TOKEN in .env file!")
        print("   1. Talk to @BotFather on Telegram")
        print("   2. Send /newbot and follow the steps")
        print("   3. Copy the token to .env")
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        print("ERROR: Please set GEMINI_API_KEY in .env file!")
        print("   1. Go to https://aistudio.google.com/apikey")
        print("   2. Create an API key")
        print("   3. Copy it to .env")
        return

    print("Reelbox Bot starting...")

    app = Application.builder().token(token).post_init(post_init).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("web", dashboard_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("browse", browse_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CallbackQueryHandler(category_button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
