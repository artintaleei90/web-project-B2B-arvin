import os
import json
import mimetypes
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_DIR = Path(__file__).resolve().parent

# بهتره توکن فقط از env خونده بشه، نه hardcode
DEFAULT_TOKEN = "8901685843:AAGIeS4fFwq4tYIQTF9m6VpsmEWrMTAULs0"


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
    return None


def _post_form(token, method, fields, files=None):
    """ارسال multipart/form-data به Telegram Bot API با هندل خطا."""
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

    url = f"https://api.telegram.org/bot{token}/{method}"
    req = Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=120) as response:
            return response.read()
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Telegram API error on '{method}' ({e.code}): {detail}"
        ) from e
    except URLError as e:
        raise RuntimeError(f"Network error calling Telegram '{method}': {e}") from e


def _send_message(token, chat_id, text, keyboard=None):
    fields = {
        "chat_id": str(chat_id),
        "text": text[:4096],
    }
    if keyboard:
        fields["reply_markup"] = json.dumps(
            keyboard, ensure_ascii=False, separators=(",", ":")
        )
    _post_form(token, "sendMessage", fields)


def _send_attachment(token, chat_id, item):
    raw_path = item.get("path")
    if not raw_path:
        return

    path = (BASE_DIR / raw_path).resolve()
    try:
        path.relative_to(BASE_DIR.resolve())
    except ValueError:
        # مسیر خارج از BASE_DIR — نادیده بگیر
        return

    if not path.is_file():
        return

    content = path.read_bytes()
    caption = (item.get("caption") or "")[:1024]
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    # برای پایداری بیشتر، همه‌چیز رو با sendDocument بفرست
    # (sendPhoto روی بعضی فرمت‌ها/ابعاد خطا می‌ده)
    if mime.startswith("image/") and mime in (
        "image/jpeg",
        "image/png",
        "image/webp",
    ):
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
    )


def send_approval(text: str, chat_id: int, item_id: str, kind: str, attachments=None):
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or DEFAULT_TOKEN).strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است.")

    keyboard = _keyboard(kind, item_id)
    attachments = attachments or []

    # برای registration: اول فایل‌ها، بعد متن + دکمه‌ها
    if kind == "registration":
        for item in attachments:
            try:
                _send_attachment(token, chat_id, item)
            except Exception as e:
                print(f"[telegram] attachment failed: {e}")
        _send_message(token, chat_id, text, keyboard)
    else:
        _send_message(token, chat_id, text, keyboard)
        for item in attachments:
            try:
                _send_attachment(token, chat_id, item)
            except Exception as e:
                print(f"[telegram] attachment failed: {e}")