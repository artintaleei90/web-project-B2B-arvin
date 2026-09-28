import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("SANAT_DB", str(BASE_DIR / "sanat_market.db"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6933858510"))


def db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def apply_action(action: str, user_id: str):
    """منطق تأیید/رد؛ (متن نتیجه) یا None برگردانده می‌شود. جدا از تلگرام تا قابل تست باشد."""
    conn = db()
    try:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return "⚠️ کاربر پیدا نشد."

        if action == "approve":
            conn.execute("UPDATE users SET status='approved', rejected_at=NULL WHERE id=?", (user_id,))
            result = "✅ حساب تأیید شد و فعال است."
        elif action == "reject":
            conn.execute(
                "UPDATE users SET status='rejected', rejected_at=?, description_pending=NULL WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), user_id),
            )
            # نشست‌های فعال کاربر رد‌شده بسته می‌شود
            conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            result = "❌ حساب رد شد. ثبت‌نام مجدد تا ۵ روز مسدود است."
        elif action == "description_approve":
            if user["status"] != "approved":
                result = "⚠️ این حساب فعال نیست."
            elif user["description_pending"] is None:
                result = "ℹ️ درخواست توضیحات دیگری وجود ندارد."
            else:
                conn.execute(
                    "UPDATE users SET description=description_pending, description_pending=NULL WHERE id=?",
                    (user_id,),
                )
                result = "✅ توضیحات پروفایل تأیید و اعمال شد."
        elif action == "description_reject":
            conn.execute("UPDATE users SET description_pending=NULL WHERE id=?", (user_id,))
            result = "❌ توضیحات جدید رد شد؛ حساب کاربر همچنان فعال است."
        else:
            return None
        conn.commit()
        return result
    finally:
        conn.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # فقط ادمین حق تأیید/رد دارد
    if not query.from_user or query.from_user.id != ADMIN_CHAT_ID:
        await query.answer(
            "شما مجاز به این کار نیستید.",
            show_alert=True
        )
        return

    await query.answer()

    try:
        action, user_id = query.data.split(":", 1)
    except (ValueError, AttributeError):
        return

    result = apply_action(action, user_id)

    if result is None:
        return

    try:
        message = query.message

        # اگر پیام عکس است، caption را ویرایش کن
        if message.photo:
            old_caption = message.caption or ""
            new_caption = old_caption + "\n\n" + result

            await query.edit_message_caption(
                caption=new_caption[:1024],
                reply_markup=None
            )

        # اگر پیام متنی بود
        else:
            old_text = message.text or ""
            new_text = old_text + "\n\n" + result

            await query.edit_message_text(
                text=new_text,
                reply_markup=None
            )

    except BadRequest as exc:
        print(f"[Telegram] خطا در ویرایش پیام: {exc}")
def check_messages():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8901685843:AAGIeS4fFwq4tYIQTF9m6VpsmEWrMTAULs0").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN تنظیم نشده است (فایل .env را بررسی کنید).")
    application = Application.builder().token(token).build()
    application.add_handler(CallbackQueryHandler(
        button_handler,
        pattern=r"^(approve|reject|description_approve|description_reject):",
    ))
    print("Callback listener started...")
    application.run_polling(allowed_updates=["callback_query"])


if __name__ == "__main__":
    check_messages()
