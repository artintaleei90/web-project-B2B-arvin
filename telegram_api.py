import os
import json
import mimetypes
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_DIR = Path(__file__).resolve().parent

# بهتره توکن فقط از env خونده بشه، نه hardcode
DEFAULT_TOKEN = "1558331832:izeJm4eKh_m2VIes4C-m5_r0jP68Dy48iAM"

def _keyboard(kind: str, item_id: str):
    if kind == "registration":
        return {"inline_keyboard": [[
            {"text": "✅ تأیید حساب", "callback_data": f"approve:{item_id}"},
            {"text": "❌ رد حساب", "callback_data": f"reject:{item_id}"},
        ]]}
    if kind == "project":
        return {"inline_keyboard": [[
            {"text": "✅ تأیید پروژه", "callback_data": f"project_approve:{item_id}"},
            {"text": "❌ رد پروژه", "callback_data": f"project_reject:{item_id}"},
        ]]}
    if kind == "description":
        return {"inline_keyboard": [[
            {"text": "✅ تأیید توضیحات", "callback_data": f"description_approve:{item_id}"},
            {"text": "❌ رد توضیحات", "callback_data": f"description_reject:{item_id}"},
        ]]}
    if kind == "profile":
        return {"inline_keyboard": [[
            {"text": "✅ تأیید پروفایل", "callback_data": f"profile_approve:{item_id}"},
            {"text": "❌ رد ویرایش", "callback_data": f"profile_reject:{item_id}"},
        ]]}
    if kind == "chat_message":
        return {"inline_keyboard": [[
            {"text": "✅ تأیید و ارسال پیام", "callback_data": f"chat_approve:{item_id}"},
            {"text": "❌ رد امنیتی", "callback_data": f"chat_reject:{item_id}"},
        ]]}
    return None


def _post_form(token, method, fields, files=None, timeout=300, retries=3):
    """ارسال multipart/form-data به Telegram Bot API با retry و timeout بالاتر."""
    boundary = uuid.uuid4().hex
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        )
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for name, (filename, content_type, content) in (files or {}).items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())

    url = f"https://tapi.bale.ai/bot{token}/{method}"
    data = bytes(body)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, data=data, headers=headers, method="POST")
            with urlopen(req, timeout=timeout) as response:
                return response.read()
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            # خطاهای ۴xx معمولاً retry نمی‌خواهند (مگر 429)
            if e.code == 429 or e.code >= 500:
                last_err = RuntimeError(
                    f"Telegram API error on '{method}' ({e.code}): {detail}"
                )
                time.sleep(min(2 ** attempt, 8))
                continue
            raise RuntimeError(
                f"Telegram API error on '{method}' ({e.code}): {detail}"
            ) from e
        except (URLError, TimeoutError, OSError) as e:
            last_err = RuntimeError(f"Network/timeout error calling Telegram '{method}' (try {attempt}/{retries}): {e}")
            time.sleep(min(2 ** attempt, 8))
            continue

    raise last_err or RuntimeError(f"Failed to call Telegram '{method}' after {retries} attempts")


def _send_message(token, chat_id, text, keyboard=None):
    fields = {
        "chat_id": str(chat_id),
        "text": text[:4096],
    }
    if keyboard:
        fields["reply_markup"] = json.dumps(
            keyboard, ensure_ascii=False, separators=(",", ":")
        )
    _post_form(token, "sendMessage", fields, timeout=60, retries=2)


def _send_attachment(token, chat_id, item):
    raw_path = item.get("path")
    if not raw_path:
        return

    path = (BASE_DIR / raw_path).resolve()
    try:
        path.relative_to(BASE_DIR.resolve())
    except ValueError:
        return

    if not path.is_file():
        return

    content = path.read_bytes()
    # فایل‌های خیلی بزرگ (>9.5MB) ممکن است تایم‌اوت یا رد شوند
    if len(content) > 9_500_000:
        print(f"[telegram] skip oversized file: {path.name} ({len(content)} bytes)")
        return

    caption = (item.get("caption") or "")[:1024]
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    # تصاویر کوچک‌تر با sendPhoto پایدارترند؛ بقیه با sendDocument
    if mime.startswith("image/") and mime in (
        "image/jpeg",
        "image/png",
        "image/webp",
    ) and len(content) < 5_000_000:
        method = "sendPhoto"
        field_name = "photo"
    else:
        method = "sendDocument"
        field_name = "document"

    _post_form(
        token,
        method,
        {"chat_id": str(chat_id), "caption": caption},
        {field_name: (path.name, mime, content)},
        timeout=300,
        retries=3,
    )


def send_approval(text: str, chat_id: int, item_id: str, kind: str, attachments=None):
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or DEFAULT_TOKEN).strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است.")

    keyboard = _keyboard(kind, item_id)
    attachments = attachments or []

    # ابتدا همه فایل‌ها (با فاصله کوتاه بین هر کدام تا rate-limit نخوریم)
    # سپس پیام اصلی همراه دکمه‌های تأیید/رد ارسال می‌شود.
    for i, item in enumerate(attachments):
        try:
            _send_attachment(token, chat_id, item)
            if i < len(attachments) - 1:
                time.sleep(0.4)
        except Exception as e:
            print(f"[telegram] attachment failed ({item.get('path')}): {e}")

    try:
        _send_message(token, chat_id, text, keyboard)
    except Exception as e:
        print(f"[telegram] message failed: {e}")
        raise
