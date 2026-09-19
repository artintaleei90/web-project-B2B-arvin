import os
SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sanaat.db")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "dev-webhook-secret")
ADMIN_TG_IDS = {int(x) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()}
ADMIN_CHAT = os.getenv("ADMIN_NOTIFY_CHAT_ID", "")
CONNECTION_FEE = int(os.getenv("CONNECTION_FEE", "500000"))
FREE_PROPOSALS = int(os.getenv("FREE_PROPOSALS", "3"))
MAX_UPLOAD = 5 * 1024 * 1024
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
