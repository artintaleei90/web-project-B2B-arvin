import httpx
from sqlalchemy.orm import Session
from .models import Notification, AuditLog
from . import config

def audit(db: Session, actor, action, entity, eid, detail=""):
    db.add(AuditLog(actor=str(actor), action=action, entity=entity, entity_id=eid, detail=detail))

def tg(method: str, payload: dict):
    if not config.TG_TOKEN:
        return None
    try:
        r = httpx.post(f"https://api.telegram.org/bot{config.TG_TOKEN}/{method}", json=payload, timeout=10)
        return r.json()
    except httpx.HTTPError:
        return None

def notify_admin(text: str, buttons=None):
    if not config.ADMIN_CHAT:
        return None
    payload = {"chat_id": config.ADMIN_CHAT, "text": text}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return tg("sendMessage", payload)

def notify(db: Session, user_id, event: str, text: str, admin=False, buttons=None):
    if user_id:
        db.add(Notification(user_id=user_id, event=event, text=text))
    if admin:
        return notify_admin(f"🔔 {event}\n{text}", buttons)
