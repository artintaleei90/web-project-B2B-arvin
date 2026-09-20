# صنعت مارکت

پلتفرم B2B صنعتی با FastAPI، SQLAlchemy و رابط RTL فارسی.

## اجرا

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python seed_admin.py admin@example.com 'StrongPass123'
uvicorn app.main:app --reload
```

سایت: `http://localhost:8000`
مستندات API: `http://localhost:8000/docs`

## تنظیمات

مقادیر واقعی را در Environment Variables قرار دهید و هرگز داخل Git یا Frontend قرار ندهید. برای Production استفاده از PostgreSQL توصیه می‌شود؛ `DATABASE_URL` از PostgreSQL با SQLAlchemy/psycopg پشتیبانی می‌کند.

## Telegram

`TELEGRAM_BOT_TOKEN`، `TELEGRAM_WEBHOOK_SECRET`، `TELEGRAM_ADMIN_IDS` و `ADMIN_NOTIFY_CHAT_ID` را تنظیم کنید. وب‌هوک باید به مسیر `/api/telegram/webhook/<secret>` متصل شود. تمام callbackهای مدیریتی در Backend احراز هویت و Audit می‌شوند.

## تست

```bash
python tests_flow.py
```

تست جریان اصلی شامل ثبت‌نام، ثبت و تأیید پروژه، پیشنهاد، انتخاب، قبول اتصال، فاکتور، تأیید پرداخت، قرارداد، تکمیل و Review است.

## Render

برای Web Service روی Render، Dockerfile پروژه به‌صورت خودکار از متغیر `PORT` سرویس استفاده می‌کند. برای Production بهتر است `DATABASE_URL` را روی PostgreSQL تنظیم کنید.
