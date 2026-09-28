import os
import asyncio
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
ALBUM_BATCH = 10  # تلگرام در هر آلبوم حداکثر ۱۰ فایل قبول می‌کند


def _abs_path(rel_path: str) -> Path:
    p = Path(rel_path)
    if p.is_absolute():
        return p
    return Path(__file__).resolve().parent / p


def _build_markup(user_id: str, kind: str):
    if kind == "description":
        keyboard = [[
            InlineKeyboardButton("✅ تأیید توضیحات",
                                 callback_data=f"description_approve:{user_id}"),
            InlineKeyboardButton("❌ رد توضیحات",
                                 callback_data=f"description_reject:{user_id}")
        ]]
    else:
        keyboard = [[
            InlineKeyboardButton("✅ تأیید", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton("❌ رد",   callback_data=f"reject:{user_id}")
        ]]
    return InlineKeyboardMarkup(keyboard)


async def _send_with_retry(send_func, retries=3):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return await send_func()
        except Exception as exc:
            last_error = exc
            print(f"[Telegram] ارسال ناموفق (تلاش {attempt}/{retries}): "
                  f"{type(exc).__name__}: {exc}")
            if attempt < retries:
                await asyncio.sleep(3)
    raise last_error


async def _send_album(app, admin_chat_id, paths, batch_size=ALBUM_BATCH):
    """ارسال لیستی از فایل‌ها به صورت آلبوم‌های گروهی (هر آلبوم حداکثر ۱۰ تا)."""
    if not paths:
        return

    for i in range(0, len(paths), batch_size):
        batch = paths[i:i + batch_size]
        media = []
        handles = []

        try:
            for p in batch:
                f = p.open("rb")
                handles.append(f)
                if p.suffix.lower() in IMAGE_EXTENSIONS:
                    media.append(InputMediaPhoto(media=f))
                else:
                    media.append(InputMediaDocument(media=f))

            await _send_with_retry(
                lambda m=media: app.bot.send_media_group(
                    chat_id=admin_chat_id, media=m
                )
            )
            print(f"[Telegram] آلبوم {i//batch_size + 1} "
                  f"({len(batch)} فایل) ارسال شد.")
        except Exception as exc:
            print(f"[Telegram] ارسال آلبوم ناموفق: {exc}")

            # اگر آلبوم شکست خورد، تک‌تک تلاش کن
            for p in batch:
                try:
                    f = p.open("rb")
                    try:
                        if p.suffix.lower() in IMAGE_EXTENSIONS:
                            await app.bot.send_photo(chat_id=admin_chat_id, photo=f)
                        else:
                            await app.bot.send_document(chat_id=admin_chat_id, document=f)
                    finally:
                        f.close()
                except Exception as exc2:
                    print(f"[Telegram] ارسال تکی {p.name} ناموفق: {exc2}")
        finally:
            for f in handles:
                try:
                    f.close()
                except Exception:
                    pass

        # رعایت rate limit تلگرام بین آلبوم‌ها
        if i + batch_size < len(paths):
            await asyncio.sleep(1)


async def _send(text, admin_chat_id, user_id, kind, attachments=None):
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=120.0,
        write_timeout=120.0,
        pool_timeout=30.0,
        media_write_timeout=180.0,
    )
    app = (Application.builder().token(TOKEN).request(request).build())

    attachments = [x for x in (attachments or []) if x]
    markup = _build_markup(user_id, kind)

    try:
        await app.initialize()

        # --------- حالت بدون فایل: فقط پیام متنی با دکمه‌ها ---------
        if not attachments:
            await _send_with_retry(
                lambda: app.bot.send_message(
                    chat_id=admin_chat_id, text=text, reply_markup=markup
                )
            )
            return

        # --------- ۱. کارت ملی: عکس/سند با caption و دکمه‌ها ---------
        first = _abs_path(attachments[0])

        if not first.exists():
            print(f"[Telegram] کارت ملی پیدا نشد: {first}")
            await _send_with_retry(
                lambda: app.bot.send_message(
                    chat_id=admin_chat_id, text=text, reply_markup=markup
                )
            )
        else:
            suffix = first.suffix.lower()
            caption = text[:1024]
            print(f"[Telegram] ارسال کارت ملی: {first.name} | "
                  f"{first.stat().st_size / 1024 / 1024:.2f} MB")

            if suffix in IMAGE_EXTENSIONS:
                def send_photo():
                    f = first.open("rb")
                    async def _do():
                        try:
                            return await app.bot.send_photo(
                                chat_id=admin_chat_id, photo=f,
                                caption=caption, reply_markup=markup
                            )
                        finally:
                            f.close()
                    return _do()
                await _send_with_retry(send_photo)
            else:
                def send_document():
                    f = first.open("rb")
                    async def _do():
                        try:
                            return await app.bot.send_document(
                                chat_id=admin_chat_id, document=f,
                                caption=caption, reply_markup=markup
                            )
                        finally:
                            f.close()
                    return _do()
                await _send_with_retry(send_document)

            print("[Telegram] کارت ملی ارسال شد.")

        # --------- ۲. بقیه فایل‌ها: نمونه‌کار + مدارک شرکت ---------
        rest_paths = [_abs_path(p) for p in attachments[1:]]
        rest_paths = [p for p in rest_paths if p.exists()]

        if rest_paths:
            header = f"📎 تصاویر نمونه‌کار و مدارک شرکت ({len(rest_paths)} فایل)"
            await _send_with_retry(
                lambda: app.bot.send_message(
                    chat_id=admin_chat_id, text=header
                )
            )
            await _send_album(app, admin_chat_id, rest_paths)
            print(f"[Telegram] مجموعاً {len(rest_paths)} فایل ضمیمه ارسال شد.")

    finally:
        try:
            await app.shutdown()
        except Exception as exc:
            print(f"[Telegram] shutdown error: {exc}")


def send_approval(text, admin_chat_id, user_id, kind="registration", attachments=None):
    asyncio.run(_send(text, admin_chat_id, user_id, kind, attachments))