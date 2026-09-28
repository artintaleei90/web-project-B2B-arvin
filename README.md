# صنعت مارکت

## نصب و اجرا
```
pip install -r requirements.txt
copy .env.example .env        (لینوکس/مک: cp .env.example .env)
# در .env توکن جدید ربات را بگذارید

# ترمینال ۱ - سایت + API
uvicorn app:app --reload

# ترمینال ۲ - دکمه‌های تأیید/رد تلگرام
python check_message.py
```
سپس سایت را از **http://127.0.0.1:8000** باز کنید (نه با دابل‌کلیک روی index.html).

فایل‌های `logo.png` و `hero-industrial.png` را کنار `index.html` بگذارید.
