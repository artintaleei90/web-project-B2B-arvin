import os
import asyncio
import traceback
from pathlib import Path

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaDocument,
)
from telegram.ext import Application
from telegram.request import HTTPXRequest

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8901685843:AAGIeS4fFwq4tYIQTF9m6VpsmEWrMTAULs0").strip()
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است.")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALBUM_BATCH = 10
BASE_DIR = Path(__file__).resolve().parent


def _log(msg):
    print(msg, flush=True)


def _abs_path(rel_path):
    p = Path(rel_path)
    return p if p.is_absolute() else BASE_DIR / p


def _normalize(attachments):
    out = []
    for item in attachments or []:
        if not item:
            continue
        if isinstance(item, dict):
            if item.get("path"):
                out.append({
                    "path": str(item["path"]),
                    "caption": item.get("caption") or "",
                })
        else:
            out.append({"path": str(item), "caption": ""})
    return out


def _build_markup(user_id, kind):
    if kind == "description":
        kb = [[
            InlineKeyboardButton("✅ تأیید توضیحات",
                                 callback_data=f"description_approve:{user_id}"),
            InlineKeyboardButton("❌ رد توضیحات",
                                 callback_data=f"description_reject:{user_id}"),
        ]]
    elif kind == "project":
        kb = [[
            InlineKeyboardButton("✅ تأیید پروژه",
                                 callback_data=f"project_approve:{user_id}"),
            InlineKeyboardButton("❌ رد پروژه",
                                 callback_data=f"project_reject:{user_id}"),
        ]]
    else:
        kb = [[
            InlineKeyboardButton("✅ تأیید", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton("❌ رد",   callback_data=f"reject:{user_id}"),
        ]]
    return InlineKeyboardMarkup(kb)


async def _send_with_retry(send_func, retries=2):
    last = None
    for attempt in range(1, retries + 1):
        try:
            return await send_func()
        except Exception as exc:
            last = exc
            _log(f"[Telegram] تلاش {attempt}/{retries} ناموفق: "
                 f"{type(exc).__name__}: {exc}")
            if attempt < retries:
                await asyncio.sleep(2)
    raise last


async def _send_album(app, admin_chat_id, items, batch_size=ALBUM_BATCH):
    if not items:
        return

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        media = []
        kept = []

        _log(f"[Telegram] آلبوم {i // batch_size + 1} — {len(batch)} آیتم")

        for item in batch:
            p = _abs_path(item["path"])
            if not p.exists():
                _log(f"[Telegram]   ✗ نیست: {p}")
                continue
            try:
                data = p.read_bytes()
            except Exception as e:
                _log(f"[Telegram]   ✗ خواندن {p.name} خطا: {e}")
                continue
            _log(f"[Telegram]   • {p.name}  {len(data)/1024/1024:.2f} MB")
            caption = (item.get("caption") or "")[:1024]
            if p.suffix.lower() in IMAGE_EXTENSIONS:
                media.append(InputMediaPhoto(
                    media=data, caption=caption, filename=p.name,
                ))
            else:
                media.append(InputMediaDocument(
                    media=data, caption=caption, filename=p.name,
                ))
            kept.append((p, caption))

        if not media:
            continue

        if len(media) == 1:
            p, cap = kept[0]
            try:
                data = p.read_bytes()
                if p.suffix.lower() in IMAGE_EXTENSIONS:
                    await app.bot.send_photo(
                        chat_id=admin_chat_id, photo=data,
                        caption=cap, filename=p.name,
                    )
                else:
                    await app.bot.send_document(
                        chat_id=admin_chat_id, document=data,
                        caption=cap, filename=p.name,
                    )
                _log(f"[Telegram] ✅ تکی ارسال شد: {p.name}")
            except Exception as e:
                _log(f"[Telegram] ❌ تکی {p.name}: "
                     f"{type(e).__name__}: {e}")
                traceback.print_exc()
            continue

        try:
            _log(f"[Telegram]   >>> send_media_group ({len(media)})")
            await _send_with_retry(
                lambda m=media: app.bot.send_media_group(
                    chat_id=admin_chat_id, media=m,
                )
            )
            _log(f"[Telegram] ✅ آلبوم {i // batch_size + 1} ارسال شد")
        except Exception as exc:
            _log(f"[Telegram] ❌ آلبوم ناموفق: "
                 f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
            for p, cap in kept:
                try:
                    data = p.read_bytes()
                    if p.suffix.lower() in IMAGE_EXTENSIONS:
                        await app.bot.send_photo(
                            chat_id=admin_chat_id, photo=data,
                            caption=cap, filename=p.name,
                        )
                    else:
                        await app.bot.send_document(
                            chat_id=admin_chat_id, document=data,
                            caption=cap, filename=p.name,
                        )
                    _log(f"[Telegram]   ↳ تکی: {p.name}")
                except Exception as e2:
                    _log(f"[Telegram]   ✗ تکی {p.name}: "
                         f"{type(e2).__name__}: {e2}")

        if i + batch_size < len(items):
            await asyncio.sleep(1)


async def _send(text, admin_chat_id, user_id, kind, attachments=None):
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=180.0,
        write_timeout=180.0,
        pool_timeout=30.0,
        media_write_timeout=300.0,
    )
    app = Application.builder().token(TOKEN).request(request).build()

    items = _normalize(attachments)
    _log(f"[Telegram] _send: {len(items)} ضمیمه | kind={kind}")

    markup = _build_markup(user_id, kind)

    try:
        await app.initialize()
        _log("[Telegram] initialize OK")

        if items:
            valid = [it for it in items if _abs_path(it["path"]).exists()]
            _log(f"[Telegram] {len(valid)}/{len(items)} فایل معتبر")
            if valid:
                await _send_album(app, admin_chat_id, valid)
                _log("[Telegram] آلبوم عکس‌ها ارسال شد")
            else:
                _log("[Telegram] فایل معتبری برای ارسال نیست")
        else:
            _log("[Telegram] ضمیمه‌ای وجود ندارد")

        await _send_with_retry(
            lambda: app.bot.send_message(
                chat_id=admin_chat_id,
                text=text[:4000],
                reply_markup=markup,
            )
        )
        _log("[Telegram] پیام مشخصات ارسال شد")
        _log("[Telegram] پایان")

    except Exception as e:
        _log(f"[Telegram] _send خطا: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        try:
            await app.shutdown()
        except Exception as e:
            _log(f"[Telegram] shutdown: {e}")


def send_approval(text, admin_chat_id, user_id, kind="registration",
                  attachments=None):
    asyncio.run(_send(text, admin_chat_id, user_id, kind, attachments))