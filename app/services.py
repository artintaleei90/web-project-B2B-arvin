# services.py
import httpx
from sqlalchemy.orm import Session
from .models import Notification, AuditLog
from . import config

def audit(db: Session, actor, action, entity, eid, detail=""):
    """ثبت رویدادها در لاگ سیستم"""
    db.add(AuditLog(actor=str(actor), action=action, entity=entity, entity_id=eid, detail=detail))

def tg(method: str, payload: dict):
    """ارسال درخواست مستقیم به API تلگرام"""
    if not config.TG_TOKEN:
        return None
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{config.TG_TOKEN}/{method}", 
            json=payload, 
            timeout=10
        )
        return response.json()
    except Exception as e:
        print(f"[Telegram Error]: {e}")
        return None

def notify_admin(text: str, buttons=None):
    """ارسال پیام اعلان به چت مدیریت در تلگرام"""
    if not config.ADMIN_CHAT:
        return None
    p = {"chat_id": config.ADMIN_CHAT, "text": text}
    if buttons:
        p["reply_markup"] = {"inline_keyboard": buttons}
    return tg("sendMessage", p)

def notify(db: Session, user_id, event: str, text: str, admin=False, buttons=None):
    """مرکز مدیریت اعلان‌های کاربر و ادمین"""
    if user_id:
        db.add(Notification(user_id=user_id, event=event, text=text))
    if admin:
        return notify_admin(f"🔔 {event}\n{text}", buttons)