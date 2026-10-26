"""
Reelbox Unified Runner
Runs both the FastAPI Web Dashboard and the Telegram Bot concurrently.
Perfect for local 1-click startup and 24/7 cloud deployments (Render, Railway, etc.).
"""

import os
import sys
import subprocess
import signal

def main():
    print("=" * 60)
    print("  🚀 REELBOX - STARTING WEB DASHBOARD & TELEGRAM BOT")
    print("=" * 60)

    # 1. Start Telegram Bot in background subprocess
    print("[RUNNER] Starting Telegram bot process...")
    bot_proc = subprocess.Popen([sys.executable, "bot.py"])

    # 2. Configure Host and Port for Web Dashboard
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[RUNNER] Starting Web Dashboard on {host}:{port}...")

    def cleanup(signum, frame):
        print("\n[RUNNER] Shutting down cleanly...")
        bot_proc.terminate()
        try:
            bot_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        import uvicorn
        uvicorn.run("dashboard:app", host=host, port=port, log_level="info")
    except Exception as e:
        print(f"[RUNNER] Web server stopped: {e}")
    finally:
        bot_proc.terminate()
        bot_proc.wait()

if __name__ == "__main__":
    main()
