import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-32chars-minimum")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'sanaat.db'}")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "change-webhook-secret")
ADMIN_TG_IDS = {int(x.strip()) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip().isdigit()}
ADMIN_CHAT = os.getenv("ADMIN_NOTIFY_CHAT_ID", "")
CONNECTION_FEE = int(os.getenv("CONNECTION_FEE", "500000"))
FREE_PROPOSALS = int(os.getenv("FREE_PROPOSALS", "3"))
TOKEN_TTL = int(os.getenv("TOKEN_TTL", str(7 * 24 * 3600)))
MAX_UPLOAD = 5 * 1024 * 1024
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
FRONTEND_ORIGINS = [x.strip() for x in os.getenv("FRONTEND_ORIGINS", "*").split(",") if x.strip()]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
