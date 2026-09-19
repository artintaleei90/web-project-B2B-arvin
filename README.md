# صنعت مارکت — Sanaat Market

بک‌اند FastAPI + SQLAlchemy و صفحه اصلی (frontend/index.html).

## اجرا
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt "pydantic[email]"
    cp .env.example .env   # مقادیر را تنظیم کنید و export کنید
    python seed_admin.py admin@example.com 'StrongPass123'
    uvicorn app.main:app --reload
مستندات API: http://localhost:8000/docs  —  تست جریان کامل: `python tests_flow.py`

## ربات تلگرام
1. با BotFather ربات بسازید و توکن را در TELEGRAM_BOT_TOKEN بگذارید.
2. آیدی عددی ادمین‌ها را در TELEGRAM_ADMIN_IDS (جداشده با کاما) و چت اعلان‌ها را در ADMIN_NOTIFY_CHAT_ID بگذارید.
3. وب‌هوک: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR-DOMAIN/api/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`
ربات منطقی ندارد؛ هر callback در بک‌اند اعتبارسنجی و لاگ می‌شود.

## پیاده‌شده
احراز هویت و نقش‌ها، ثبت پروژه با تأیید ادمین، پیشنهاد (یک فعال + سهم رایگان)، انتخاب/اتصال، چت با حذف اطلاعات تماس،
فاکتور با کد N، تأیید/رد پرداخت از وب و تلگرام، آزادسازی تماس، قرارداد دوطرفه + بررسی ادمین، لغو، پایان دوطرفه، امتیازدهی،
اعلان مرکزی، آپلود امن، Audit Log، ماشین وضعیت پروژه.

## باقی‌مانده (قبل از Production)
- رابط کاربری داشبوردها/فرم‌ها/چت (فقط صفحه اصلی آماده است) و اتصال به API
- مهاجرت دیتابیس (Alembic) و PostgreSQL، ذخیره‌سازی فایل خارج از دیسک محلی، HTTPS و محدودسازی CORS
- صفحات SEO شهر/خدمت، sitemap، مدیریت خدمات/دسته‌ها/اختلاف/اشتراک از پنل ادمین
- فیلتر تماس بهترین‌تلاش است و قابل دور زدن؛ بازبینی ادمین لازم است
