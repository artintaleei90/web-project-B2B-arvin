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


def apply_action(action: str, target_id: str):
    """منطق تأیید/رد؛ (متن نتیجه) یا None برمی‌گرداند."""
    conn = db()
    try:
        # ---------- actions مربوط به کاربر ----------
        if action in ("approve", "reject", "description_approve", "description_reject"):
            user = conn.execute("SELECT * FROM users WHERE id=?", (target_id,)).fetchone()
            if not user:
                return "⚠️ کاربر پیدا نشد."

            if action == "approve":
                conn.execute("UPDATE users SET status='approved', rejected_at=NULL WHERE id=?", (target_id,))
                result = "✅ حساب تأیید شد و فعال است."
            elif action == "reject":
                conn.execute(
                    "UPDATE users SET status='rejected', rejected_at=?, description_pending=NULL WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), target_id),
                )
                conn.execute("DELETE FROM sessions WHERE user_id=?", (target_id,))
                result = "❌ حساب رد شد. ثبت‌نام مجدد تا ۵ روز مسدود است."
            elif action == "description_approve":
                if user["status"] != "approved":
                    result = "⚠️ این حساب فعال نیست."
                elif user["description_pending"] is None:
                    result = "ℹ️ درخواست توضیحات دیگری وجود ندارد."
                else:
                    conn.execute(
                        "UPDATE users SET description=description_pending, description_pending=NULL WHERE id=?",
                        (target_id,),
                    )
                    result = "✅ توضیحات پروفایل تأیید و اعمال شد."
            elif action == "description_reject":
                conn.execute("UPDATE users SET description_pending=NULL WHERE id=?", (target_id,))
                result = "❌ توضیحات جدید رد شد؛ حساب کاربر همچنان فعال است."
            else:
                return None

        # ---------- actions مربوط به پروژه ----------
        elif action in ("project_approve", "project_reject"):
            project = conn.execute("SELECT * FROM projects WHERE id=?", (target_id,)).fetchone()
            if not project:
                return "⚠️ پروژه پیدا نشد."

            if action == "project_approve":
                conn.execute(
                    "UPDATE projects SET status='approved', reviewed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), target_id),
                )
                result = "✅ پروژه تأیید و به لیست عمومی اضافه شد."
            else:
                conn.execute(
                    "UPDATE projects SET status='rejected', reviewed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), target_id),
                )
                result = "❌ پروژه رد شد."

        else:
            return None

        conn.commit()
        return result
    finally:
        conn.close()


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query.from_user or query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("شما مجاز به این کار نیستید.", show_alert=True)
        return

    await query.answer()

    try:
        action, target_id = query.data.split(":", 1)
    except (ValueError, AttributeError):
        return

    result = apply_action(action, target_id)
    if result is None:
        return

    try:
        message = query.message
        if message.photo:
            old = message.caption or ""
            new = old + "\n\n" + result
            await query.edit_message_caption(caption=new[:1024], reply_markup=None)
        else:
            old = message.text or ""
            new = old + "\n\n" + result
            await query.edit_message_text(text=new[:4000], reply_markup=None)
    except BadRequest as exc:
        print(f"[Telegram] خطا در ویرایش پیام: {exc}", flush=True)


def check_messages():
    """
    این تابع را هم می‌توان از app.py در یک thread صدا زد،
    و هم مستقیم با `python check_message.py` اجرا کرد.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN",
                      "8901685843:AAGIeS4fFwq4tYIQTF9m6VpsmEWrMTAULs0").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN تنظیم نشده است.")

    application = Application.builder().token(token).build()
    application.add_handler(CallbackQueryHandler(
        button_handler,
        pattern=r"^(approve|reject|description_approve|description_reject|"
                r"project_approve|project_reject):",
    ))
    print("Callback listener started...", flush=True)

    # stop_signals=None  → چون در thread جدا اجرا می‌شود، سیگنال‌های OS را دست نزن
    # close_loop=True    → loop ساخته‌شده در همین thread بسته شود
    application.run_polling(
        allowed_updates=["callback_query"],
        stop_signals=None,
        close_loop=True,
    )


if __name__ == "__main__":
    check_messages()