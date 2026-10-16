import os
import sqlite3
import json
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


def apply_action(action: str, item_id: str):
    conn = db()
    try:
        if action in ("approve", "reject", "description_approve", "description_reject",
                      "profile_approve", "profile_reject"):
            user = conn.execute(
                "SELECT * FROM users WHERE id=?", (item_id,)
            ).fetchone()
            if not user:
                return "⚠️ کاربر پیدا نشد."

            if action == "approve":
                conn.execute(
                    """UPDATE users
                       SET status='approved', rejected_at=NULL
                       WHERE id=?""",
                    (item_id,),
                )
                result = "✅ حساب تأیید شد و فعال است."

            elif action == "reject":
                conn.execute(
                    """UPDATE users
                       SET status='rejected',
                           rejected_at=?,
                           description_pending=NULL,
                           profile_pending_json=NULL
                       WHERE id=?""",
                    (datetime.now(timezone.utc).isoformat(), item_id),
                )
                conn.execute(
                    "DELETE FROM sessions WHERE user_id=?", (item_id,)
                )
                result = "❌ حساب رد شد. ثبت‌نام مجدد تا ۵ روز مسدود است."

            elif action == "description_approve":
                if user["status"] != "approved":
                    result = "⚠️ این حساب فعال نیست."
                elif user["description_pending"] is None:
                    result = "ℹ️ درخواست توضیحات دیگری وجود ندارد."
                else:
                    conn.execute(
                        """UPDATE users
                           SET description=description_pending,
                               description_pending=NULL
                           WHERE id=?""",
                        (item_id,),
                    )
                    result = "✅ توضیحات پروفایل تأیید و اعمال شد."

            elif action == "description_reject":
                conn.execute(
                    "UPDATE users SET description_pending=NULL WHERE id=?",
                    (item_id,),
                )
                result = "❌ توضیحات جدید رد شد؛ حساب کاربر همچنان فعال است."

            elif action == "profile_approve":
                pending_raw = user["profile_pending_json"]
                if not pending_raw:
                    result = "ℹ️ درخواست ویرایش پروفایلی وجود ندارد."
                else:
                    try:
                        pending = json.loads(pending_raw)
                    except Exception:
                        pending = None

                    if not isinstance(pending, dict):
                        result = "⚠️ اطلاعات ویرایش پروفایل قابل خواندن نیست."
                    else:
                        conn.execute(
                            """UPDATE users SET
                               first_name=?, last_name=?, birth_date=?, gender=?,
                               phone=?, activity_city=?, activity_field=?,
                               work_history=?, description=?, company_name=?,
                               company_id=?, role=?, profile_pending_json=NULL,
                               status='approved', rejected_at=NULL
                               WHERE id=?""",
                            (
                                pending.get("first_name", user["first_name"]),
                                pending.get("last_name", user["last_name"]),
                                pending.get("birth_date", user["birth_date"]),
                                pending.get("gender", user["gender"]),
                                pending.get("phone", user["phone"]),
                                pending.get("activity_city", user["activity_city"]),
                                pending.get("activity_field", user["activity_field"]),
                                pending.get("work_history", ""),
                                pending.get("description", ""),
                                pending.get("company_name"),
                                pending.get("company_id"),
                                pending.get("role", user["role"]),
                                item_id,
                            ),
                        )
                        result = "✅ ویرایش پروفایل تأیید شد و حساب دوباره فعال است."

            else:  # profile_reject
                conn.execute(
                    """UPDATE users
                       SET profile_pending_json=NULL,
                           status='approved',
                           rejected_at=NULL
                       WHERE id=?""",
                    (item_id,),
                )
                result = "❌ ویرایش پروفایل رد شد؛ اطلاعات قبلی حفظ شد و حساب فعال ماند."

        elif action in ("chat_approve", "chat_reject"):
            pending = conn.execute(
                "SELECT * FROM pending_chat_messages WHERE id=?", (item_id,)
            ).fetchone()
            if not pending:
                return "⚠️ پیام پیدا نشد."
            if pending["status"] != "pending":
                return "ℹ️ این پیام قبلاً بررسی شده است."
            sender = pending["sender_id"]
            request = conn.execute(
                """SELECT r.*, p.user_id AS employer_id, p.title AS project_title
                   FROM project_requests r JOIN projects p ON p.id=r.project_id
                   WHERE r.id=?""", (pending["request_id"],)
            ).fetchone()
            if not request:
                conn.execute("UPDATE pending_chat_messages SET status='rejected',decided_at=? WHERE id=?",
                             (datetime.now(timezone.utc).isoformat(), item_id))
                result = "❌ گفتگو پیدا نشد؛ پیام رد شد."
            elif action == "chat_approve":
                conn.execute(
                    "INSERT INTO project_chat_messages(id,request_id,sender_id,body,created_at) VALUES(?,?,?,?,?)",
                    (item_id, pending["request_id"], sender, pending["body"], datetime.now(timezone.utc).isoformat())
                )
                other = request["contractor_id"] if sender == request["employer_id"] else request["employer_id"]
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",
                             (__import__("secrets").token_hex(16), other, "chat_message", request["project_id"], pending["request_id"], 0, now))
                conn.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",
                             (__import__("secrets").token_hex(16), sender, "message_approved", request["project_id"], pending["request_id"], 0, now))
                conn.execute("UPDATE pending_chat_messages SET status='approved',decided_at=? WHERE id=?",
                             (now, item_id))
                result = "✅ پیام تأیید شد و برای طرف مقابل ارسال شد."
            else:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("UPDATE pending_chat_messages SET status='rejected',decided_at=? WHERE id=?", (now, item_id))
                conn.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",
                             (__import__("secrets").token_hex(16), sender, "message_rejected", request["project_id"], pending["request_id"], 0, now))
                result = "❌ پیام به دلیل ملاحظات امنیتی رد شد."

        elif action in ("project_approve", "project_reject"):
            project = conn.execute(
                """SELECT p.*, u.status AS owner_status
                   FROM projects p JOIN users u ON u.id=p.user_id
                   WHERE p.id=?""",
                (item_id,),
            ).fetchone()

            if not project:
                return "⚠️ پروژه پیدا نشد."

            if action == "project_approve":
                if project["owner_status"] != "approved":
                    result = "⚠️ حساب کارفرمای پروژه هنوز تأیید نشده است."
                else:
                    conn.execute(
                        """UPDATE projects
                           SET status='active', approved_at=?
                           WHERE id=?""",
                        (datetime.now(timezone.utc).isoformat(), item_id),
                    )
                    result = "✅ پروژه تأیید شد و به پروژه‌های فعال اضافه شد."
            else:
                conn.execute(
                    "UPDATE projects SET status='rejected', approved_at=NULL WHERE id=?",
                    (item_id,),
                )
                result = "❌ پروژه رد شد و در پروفایل کارفرما با وضعیت «رد شده» نمایش داده می‌شود."

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

    try:
        await query.answer()
    except Exception:
        pass

    try:
        action, item_id = query.data.split(":", 1)
    except (ValueError, AttributeError):
        return

    result = apply_action(action, item_id)
    if result is None:
        return

    try:
        message = query.message
        if message.photo:
            old_caption = message.caption or ""
            new_caption = old_caption + "\n\n" + result
            await query.edit_message_caption(
                caption=new_caption[:1024],
                reply_markup=None,
            )
        else:
            old_text = message.text or ""
            new_text = old_text + "\n\n" + result
            await query.edit_message_text(
                text=new_text[:4096],
                reply_markup=None,
            )
    except BadRequest as exc:
        print(f"[Telegram] خطا در ویرایش پیام: {exc}")


def check_messages():
    token = "8901685843:AAGIeS4fFwq4tYIQTF9m6VpsmEWrMTAULs0"
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN تنظیم نشده است. آن را در .env قرار دهید."
        )

    builder = Application.builder().token(token)
    proxy = os.getenv("TELEGRAM_PROXY", "").strip()
    if proxy:
        builder = builder.proxy(proxy).get_updates_proxy(proxy)
    application = builder.build()
    application.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern=r"^(approve|reject|description_approve|description_reject|profile_approve|profile_reject|project_approve|project_reject|chat_approve|chat_reject):",
        )
    )

    print("Callback listener started...")
    application.run_polling(allowed_updates=["callback_query"])


if __name__ == "__main__":
    check_messages()
