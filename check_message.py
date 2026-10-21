import os
import sqlite3
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from bale import Bot, CallbackQuery

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("SANAT_DB", str(BASE_DIR / "sanat_market.db"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "981231444"))


def db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def apply_action(action: str, item_id: str):
    """منطق تجاری بدون تغییر باقی می‌ماند."""
    conn = db()
    try:
        if action in ("approve", "reject", "description_approve", "description_reject",
                      "profile_approve", "profile_reject"):
            user = conn.execute("SELECT * FROM users WHERE id=?", (item_id,)).fetchone()
            if not user:
                return "⚠️ کاربر پیدا نشد."

            if action == "approve":
                conn.execute("UPDATE users SET status='approved', rejected_at=NULL WHERE id=?", (item_id,))
                result = "✅ حساب تأیید شد و فعال است."
            elif action == "reject":
                conn.execute(
                    "UPDATE users SET status='rejected', rejected_at=?, description_pending=NULL, profile_pending_json=NULL WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), item_id),
                )
                conn.execute("DELETE FROM sessions WHERE user_id=?", (item_id,))
                result = "❌ حساب رد شد. ثبت‌نام مجدد تا ۵ روز مسدود است."
            elif action == "description_approve":
                if user["status"] != "approved":
                    result = "⚠️ این حساب فعال نیست."
                elif user["description_pending"] is None:
                    result = "ℹ️ درخواست توضیحات دیگری وجود ندارد."
                else:
                    conn.execute("UPDATE users SET description=description_pending, description_pending=NULL WHERE id=?", (item_id,))
                    result = "✅ توضیحات پروفایل تأیید و اعمال شد."
            elif action == "description_reject":
                conn.execute("UPDATE users SET description_pending=NULL WHERE id=?", (item_id,))
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
                            """UPDATE users SET first_name=?, last_name=?, birth_date=?, gender=?, phone=?,
                               activity_city=?, activity_field=?, work_history=?, description=?, company_name=?,
                               company_id=?, role=?, profile_pending_json=NULL, status='approved', rejected_at=NULL WHERE id=?""",
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
                conn.execute("UPDATE users SET profile_pending_json=NULL, status='approved', rejected_at=NULL WHERE id=?", (item_id,))
                result = "❌ ویرایش پروفایل رد شد؛ اطلاعات قبلی حفظ شد و حساب فعال ماند."

        elif action in ("chat_approve", "chat_reject"):
            pending = conn.execute("SELECT * FROM pending_chat_messages WHERE id=?", (item_id,)).fetchone()
            if not pending:
                return "⚠️ پیام پیدا نشد."
            if pending["status"] != "pending":
                return "ℹ️ این پیام قبلاً بررسی شده است."
            sender = pending["sender_id"]
            request = conn.execute(
                "SELECT r.*, p.user_id AS employer_id, p.title AS project_title FROM project_requests r JOIN projects p ON p.id=r.project_id WHERE r.id=?",
                (pending["request_id"],)
            ).fetchone()
            if not request:
                conn.execute("UPDATE pending_chat_messages SET status='rejected',decided_at=? WHERE id=?",
                             (datetime.now(timezone.utc).isoformat(), item_id))
                result = "❌ گفتگو پیدا نشد؛ پیام رد شد."
            elif action == "chat_approve":
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO project_chat_messages(id,request_id,sender_id,body,created_at) VALUES(?,?,?,?,?)",
                    (item_id, pending["request_id"], sender, pending["body"], now)
                )
                other = request["contractor_id"] if sender == request["employer_id"] else request["employer_id"]
                conn.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",
                             (secrets.token_hex(16), other, "chat_message", request["project_id"], pending["request_id"], 0, now))
                conn.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",
                             (secrets.token_hex(16), sender, "message_approved", request["project_id"], pending["request_id"], 0, now))
                conn.execute("UPDATE pending_chat_messages SET status='approved',decided_at=? WHERE id=?", (now, item_id))
                result = "✅ پیام تأیید شد و برای طرف مقابل ارسال شد."
            else:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("UPDATE pending_chat_messages SET status='rejected',decided_at=? WHERE id=?", (now, item_id))
                conn.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",
                             (secrets.token_hex(16), sender, "message_rejected", request["project_id"], pending["request_id"], 0, now))
                result = "❌ پیام به دلیل ملاحظات امنیتی رد شد."

        elif action in ("project_approve", "project_reject"):
            project = conn.execute(
                "SELECT p.*, u.status AS owner_status FROM projects p JOIN users u ON u.id=p.user_id WHERE p.id=?",
                (item_id,),
            ).fetchone()
            if not project:
                return "⚠️ پروژه پیدا نشد."
            if action == "project_approve":
                if project["owner_status"] != "approved":
                    result = "⚠️ حساب کارفرمای پروژه هنوز تأیید نشده است."
                else:
                    conn.execute("UPDATE projects SET status='active', approved_at=? WHERE id=?",
                                 (datetime.now(timezone.utc).isoformat(), item_id))
                    result = "✅ پروژه تأیید شد و به پروژه‌های فعال اضافه شد."
            else:
                conn.execute("UPDATE projects SET status='rejected', approved_at=NULL WHERE id=?", (item_id,))
                result = "❌ پروژه رد شد و در پروفایل کارفرما با وضعیت «رد شده» نمایش داده می‌شود."
        else:
            return None

        conn.commit()
        return result
    finally:
        conn.close()


async def button_handler(callback: CallbackQuery):
    """پردازش رویداد کلیک دکمه (سازگار با python-bale-bot)."""
    print(f"[DEBUG] callback data={callback.data!r}, from_user={callback.from_user}")

    # بررسی ادمین (بدون فراخوانی callback.answer که در این کتابخانه وجود ندارد)
    if not callback.from_user or callback.from_user.id != ADMIN_CHAT_ID:
        print(f"[DEBUG] Admin check failed: expected {ADMIN_CHAT_ID}")
        return

    try:
        action, item_id = callback.data.split(":", 1)
        print(f"[DEBUG] parsed action={action!r}, item_id={item_id!r}")
    except (ValueError, AttributeError) as e:
        print(f"[DEBUG] parse error: {e}")
        return

    result = apply_action(action, item_id)
    print(f"[DEBUG] apply_action result={result!r}")
    if result is None:
        return

    message = callback.message
    if message:
        try:
            # در بله برای تشخیص وجود کپشن (تصویر/ویدیو) از caption استفاده می‌کنیم
            # اگر پیام caption داشته باشد، آن را ویرایش می‌کنیم؛ در غیر این صورت متن را
            if getattr(message, 'caption', None) is not None:
                old_caption = message.caption or ""
                new_caption = old_caption + "\n\n" + result
                await message.edit(caption=new_caption[:1024])
            else:
                old_text = message.text or ""
                new_text = old_text + "\n\n" + result
                await message.edit(text=new_text[:4096])
            print("[DEBUG] message edited successfully")
        except Exception as exc:
            print(f"[DEBUG] edit error: {exc}")


def check_messages():
    token = os.getenv("BALE_BOT_TOKEN", "1558331832:izeJm4eKh_m2VIes4C-m5_r0jP68Dy48iAM").strip()
    if not token:
        raise SystemExit("BALE_BOT_TOKEN تنظیم نشده است.")

    bot = Bot(token=token)

    @bot.event
    async def on_callback(callback: CallbackQuery):
        print(f"[DEBUG] CALLBACK RECEIVED: {callback.data}")
        await button_handler(callback)

    print("[BALE] Callback listener registered. Starting bot...")
    bot.run()


if __name__ == "__main__":
    check_messages()