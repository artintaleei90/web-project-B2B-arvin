import os
import sqlite3
import hashlib
import hmac
import secrets
import logging
import base64
import json
import mimetypes
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, field_validator

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads" / "registrations"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PROJECT_IMAGES = 20
MAX_COMPANY_DOCUMENTS = 20
DB_PATH = Path(os.getenv("SANAT_DB", str(BASE_DIR / "sanat_market.db")))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6933858510"))
SESSION_DAYS = 30
REJECT_COOLDOWN = timedelta(days=5)

log = logging.getLogger("sanat")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Sanaat Market API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- database
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            national_id TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            company_name TEXT,
            company_id TEXT,
            role TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            rejected_at TEXT,
            description_pending TEXT,
            birth_date TEXT,
            gender TEXT,
            activity_city TEXT,
            activity_field TEXT,
            work_history TEXT,
            national_id_image TEXT,
            project_samples TEXT,
            project_images TEXT,
            company_documents TEXT,
            registration_ip TEXT,
            registration_time TEXT,
            device_browser TEXT,
            request_id TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_active
            ON users(email) WHERE status != 'rejected';
        CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            employer_name TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """)

        existing = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        migrations = {
            "birth_date": "ALTER TABLE users ADD COLUMN birth_date TEXT",
            "gender": "ALTER TABLE users ADD COLUMN gender TEXT",
            "activity_city": "ALTER TABLE users ADD COLUMN activity_city TEXT",
            "activity_field": "ALTER TABLE users ADD COLUMN activity_field TEXT",
            "work_history": "ALTER TABLE users ADD COLUMN work_history TEXT",
            "national_id_image": "ALTER TABLE users ADD COLUMN national_id_image TEXT",
            "project_samples": "ALTER TABLE users ADD COLUMN project_samples TEXT",
            "project_images": "ALTER TABLE users ADD COLUMN project_images TEXT",
            "company_documents": "ALTER TABLE users ADD COLUMN company_documents TEXT",
            "registration_ip": "ALTER TABLE users ADD COLUMN registration_ip TEXT",
            "registration_time": "ALTER TABLE users ADD COLUMN registration_time TEXT",
            "device_browser": "ALTER TABLE users ADD COLUMN device_browser TEXT",
            "request_id": "ALTER TABLE users ADD COLUMN request_id TEXT",
        }
        for column, sql in migrations.items():
            if column not in existing:
                db.execute(sql)


init_db()


# ---------------------------------------------------------------- security
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 210_000)
        return hmac.compare_digest(check.hex(), digest_hex)
    except Exception:
        return False


_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
    db.execute(
        "INSERT INTO sessions (token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)",
        (_token_hash(token), user_id, now.isoformat(),
         (now + timedelta(days=SESSION_DAYS)).isoformat()),
    )
    return token


def _bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "ابتدا وارد حساب خود شوید.")
    return authorization[7:].strip()


def current_user(authorization: Optional[str] = Header(None)):
    token = _bearer(authorization)
    with get_db() as db:
        row = db.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash=? AND s.expires_at > ?""",
            (_token_hash(token), now_iso()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "نشست شما منقضی شده است. دوباره وارد شوید.")
    return row


# ---------------------------------------------------------------- validation
def validate_iran_phone(v: str) -> str:
    v = v.strip()
    if not (v.isascii() and v.isdigit() and len(v) == 11 and v.startswith("09")):
        raise ValueError("شماره تماس باید به شکل 09xxxxxxxxx باشد.")
    return v


def validate_national_id(v: str) -> str:
    v = v.strip()
    if not (v.isascii() and v.isdigit() and len(v) == 10):
        raise ValueError("کد ملی باید ۱۰ رقم باشد.")
    return v


class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    national_id: str
    birth_date: str
    gender: str
    phone: str
    email: EmailStr
    password: str
    activity_city: str
    activity_field: str
    work_history: str = ""
    description: str = ""
    national_id_image: str
    project_samples: str = ""
    project_images: list[str] = []
    company_name: Optional[str] = None
    company_id: Optional[str] = None
    role: str
    company_documents: list[str] = []

    @field_validator("first_name", "last_name")
    @classmethod
    def name_ok(cls, v):
        v = v.strip()
        if not v or len(v) > 60:
            raise ValueError("نام و نام خانوادگی الزامی است.")
        return v

    @field_validator("phone")
    @classmethod
    def phone_ok(cls, v):
        return validate_iran_phone(v)

    @field_validator("national_id")
    @classmethod
    def national_ok(cls, v):
        return validate_national_id(v)

    @field_validator("password")
    @classmethod
    def password_ok(cls, v):
        if len(v) < 8:
            raise ValueError("رمز عبور باید حداقل ۸ کاراکتر باشد.")
        if len(v) > 128:
            raise ValueError("رمز عبور بیش از حد طولانی است.")
        return v

    @field_validator("description")
    @classmethod
    def desc_ok(cls, v):
        if len(v) > 2000:
            raise ValueError("توضیحات حداکثر ۲۰۰۰ کاراکتر می‌تواند باشد.")
        return v

    @field_validator("birth_date", "gender", "activity_city", "activity_field", "role")
    @classmethod
    def required_text_ok(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("این فیلد الزامی است.")
        return v

    @field_validator("work_history", "project_samples")
    @classmethod
    def extra_text_ok(cls, v):
        if len(v) > 10000:
            raise ValueError("متن واردشده بیش از حد طولانی است.")
        return v.strip()

    @field_validator("national_id_image")
    @classmethod
    def national_image_ok(cls, v):
        if not v or not v.startswith("data:"):
            raise ValueError("تصویر کارت ملی الزامی است.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class DescriptionIn(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def desc_ok(cls, v):
        if len(v) > 2000:
            raise ValueError("توضیحات حداکثر ۲۰۰۰ کاراکتر می‌تواند باشد.")
        return v


def user_public(row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    d["has_pending_description"] = d.pop("description_pending", None) is not None
    return d


# ---------------------------------------------------------------- telegram
def send_admin_approval(user_id: str, text: str, kind: str = "registration", attachments=None):
    try:
        from telegram_api import send_approval
        send_approval(text[:4000], ADMIN_CHAT_ID, user_id, kind, attachments or [])
    except Exception:
        log.exception("Telegram notification failed")


# ---------------------------------------------------------------- file storage
def save_data_url(data_url: str, user_id: str, label: str, index: int = 0) -> str:
    if not isinstance(data_url, str) or not data_url.startswith("data:"):
        raise HTTPException(400, "فرمت فایل ارسال‌شده معتبر نیست.")
    try:
        header, encoded = data_url.split(",", 1)
        mime = header[5:].split(";", 1)[0].lower()
        if not mime.startswith("image/") and label in {"national_id", "project_image"}:
            raise HTTPException(400, "فایل تصویر باید از نوع تصویری باشد.")
        if label == "company_document" and not (mime.startswith("image/") or mime == "application/pdf"):
            raise HTTPException(400, "مدرک شرکت باید تصویر یا PDF باشد.")
        raw = base64.b64decode(encoded, validate=True)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "فایل ارسال‌شده قابل خواندن نیست.")
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(413, "حجم هر فایل نباید بیشتر از ۱۰ مگابایت باشد.")
    ext = mimetypes.guess_extension(mime) or ".bin"
    if mime == "image/jpeg": ext = ".jpg"
    if mime == "image/png": ext = ".png"
    if mime == "image/webp": ext = ".webp"
    if mime == "application/pdf": ext = ".pdf"
    folder = UPLOAD_DIR / user_id
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{label}_{index}{ext}"
    path = folder / filename
    path.write_bytes(raw)
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def save_registration_files(data: RegisterIn, user_id: str):
    national = save_data_url(data.national_id_image, user_id, "national_id")
    project_paths = []
    if len(data.project_images) > MAX_PROJECT_IMAGES:
        raise HTTPException(400, f"حداکثر {MAX_PROJECT_IMAGES} تصویر پروژه مجاز است.")
    for i, item in enumerate(data.project_images, 1):
        project_paths.append(save_data_url(item, user_id, "project_image", i))
    company_paths = []
    if len(data.company_documents) > MAX_COMPANY_DOCUMENTS:
        raise HTTPException(400, f"حداکثر {MAX_COMPANY_DOCUMENTS} مدرک شرکت مجاز است.")
    for i, item in enumerate(data.company_documents, 1):
        company_paths.append(save_data_url(item, user_id, "company_document", i))
    return national, project_paths, company_paths


# ---------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/register")
def register(data: RegisterIn, request: Request, background: BackgroundTasks):
    email = str(data.email).lower().strip()
    phone = data.phone
    company = (data.company_name or "").strip() or None
    company_id = (data.company_id or "").strip() or None
    role = (data.role or "").strip() or None
    description = data.description.strip()

    if role not in ("employer", "contractor"):
        raise HTTPException(400, "نوع فعالیت الزامی است و باید کارفرما یا پیمانکار باشد.")

    if company and not company_id:
        raise HTTPException(400, "در صورت ثبت شرکت، شناسه شرکت الزامی است.")
    if not company and data.company_documents:
        raise HTTPException(400, "برای ارسال مدارک شرکت، ابتدا نام شرکت را ثبت کنید.")

    user_id = secrets.token_hex(16)
    request_id = secrets.token_hex(12)
    registration_time = now_iso()
    registration_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        registration_ip = forwarded_for.split(",")[0].strip()
    device_browser = request.headers.get("user-agent", "unknown")[:1000]

    national_id_path, project_paths, company_paths = save_registration_files(data, user_id)
    try:
        with get_db() as db:
            rows = db.execute(
                "SELECT status, rejected_at FROM users WHERE lower(email)=? OR phone=?",
                (email, phone),
            ).fetchall()
            for r in rows:
                if r["status"] != "rejected":
                    raise HTTPException(409, "این Gmail یا شماره تماس قبلاً ثبت شده است.")
                if r["rejected_at"]:
                    rejected_at = datetime.fromisoformat(r["rejected_at"])
                    if datetime.now(timezone.utc) - rejected_at < REJECT_COOLDOWN:
                        raise HTTPException(409, "این حساب رد شده است. ثبت‌نام مجدد تا ۵ روز امکان‌پذیر نیست.")

            db.execute(
                """INSERT INTO users
                   (id,first_name,last_name,national_id,birth_date,gender,phone,email,password_hash,
                    activity_city,activity_field,work_history,description,national_id_image,project_samples,
                    project_images,company_name,company_id,role,company_documents,status,created_at,
                    registration_ip,registration_time,device_browser,request_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, data.first_name, data.last_name, data.national_id, data.birth_date, data.gender,
                 phone, email, hash_password(data.password), data.activity_city, data.activity_field,
                 data.work_history.strip(), description, national_id_path, data.project_samples.strip(),
                 json.dumps(project_paths, ensure_ascii=False), company, company_id, role,
                 json.dumps(company_paths, ensure_ascii=False), "pending", registration_time,
                 registration_ip, registration_time, device_browser, request_id),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "این Gmail یا شماره تماس قبلاً ثبت شده است.")
    except Exception:
        import shutil
        shutil.rmtree(UPLOAD_DIR / user_id, ignore_errors=True)
        raise

    role_text = {"employer": "کارفرما", "contractor": "پیمانکار"}.get(role, "ثبت نشده")
    message = f"""🆕 درخواست ثبت‌نام جدید صنعت مارکت

👤 نام: {data.first_name} {data.last_name}
🪪 کد ملی: {data.national_id}
🎂 تاریخ تولد: {data.birth_date}
⚧ جنسیت: {data.gender}
📱 شماره تماس: {phone}
📧 Gmail: {email}
📍 شهر فعالیت: {data.activity_city}
🏭 زمینه فعالیت: {data.activity_field}
📝 توضیحات: {description[:1000] or "ثبت نشده"}
💼 سابقه کاری: {data.work_history[:1000] or "ثبت نشده"}
📁 نمونه پروژه: {data.project_samples[:1000] or "ثبت نشده"}

🏢 شرکت: {company or "ندارد"}
🔑 شناسه شرکت: {company_id or "—"}
👷 نوع فعالیت: {role_text}
📎 کارت ملی: ذخیره شد
📎 تصاویر پروژه: {len(project_paths)} فایل
📎 مدارک شرکت: {len(company_paths)} فایل

🔐 اطلاعات خودکار سیستم:
🌐 IP ثبت‌نام: {registration_ip}
🕒 زمان ثبت: {registration_time}
💻 مرورگر/دستگاه: {device_browser[:500]}
🆔 شناسه کاربر: {user_id}
🧾 شناسه درخواست: {request_id}

⏳ وضعیت: در انتظار بررسی ادمین"""
    attachments = [national_id_path, *project_paths, *company_paths]
    background.add_task(send_admin_approval, user_id, message, "registration", attachments)

    # ---------- ساخت session و برگرداندن توکن ----------
    with get_db() as db:
        token = create_session(db, user_id)
        row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    return {
        "message": "ثبت‌نام با موفقیت انجام شد. حساب شما در انتظار تأیید ادمین است.",
        "user": user_public(row),
        "token": token,
        "user_id": user_id,
        "request_id": request_id,
    }


@app.post("/api/login")
def login(data: LoginIn):
    email = str(data.email).lower().strip()
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE lower(email)=? ORDER BY created_at DESC LIMIT 1", (email,)
        ).fetchone()
        ok = verify_password(data.password, row["password_hash"] if row else _DUMMY_HASH)
        if not row or not ok:
            raise HTTPException(401, "Gmail یا رمز عبور اشتباه است.")
        token = create_session(db, row["id"])
    return {"user": user_public(row), "token": token}


@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    token = _bearer(authorization)
    with get_db() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"user": user_public(user)}


@app.get("/api/profile")
def profile(user=Depends(current_user)):
    with get_db() as db:
        projects = [dict(x) for x in db.execute(
            "SELECT id,title,created_at FROM projects WHERE user_id=? ORDER BY created_at DESC",
            (user["id"],))]
        reviews = [dict(x) for x in db.execute(
            "SELECT employer_name,text,created_at FROM reviews WHERE user_id=? ORDER BY created_at DESC",
            (user["id"],))]
    return {"user": user_public(user), "projects": projects, "reviews": reviews}


@app.put("/api/profile/description")
def update_description(data: DescriptionIn, background: BackgroundTasks, user=Depends(current_user)):
    if user["status"] != "approved":
        raise HTTPException(403, "تا قبل از تأیید حساب امکان تغییر توضیحات وجود ندارد.")
    new_desc = data.description.strip()
    with get_db() as db:
        db.execute("UPDATE users SET description_pending=? WHERE id=?", (new_desc, user["id"]))

    message = f"""✏️ درخواست تغییر توضیحات پروفایل

🆔 شناسه کاربر:
{user["id"]}

👤 {user["first_name"]} {user["last_name"]}
📧 {user["email"]}

📝 توضیحات جدید:
{new_desc[:1500] or "(خالی)"}"""
    background.add_task(send_admin_approval, user["id"], message, "description")
    return {"message": "توضیحات برای بررسی ادمین ارسال شد. تا تأیید، حساب شما قفل نمی‌شود."}


# ---------------------------------------------------------------- serve the site
_PUBLIC_FILES = {"logo.png", "hero-industrial.png"}


@app.get("/", include_in_schema=False)
def index():
    f = BASE_DIR / "index.html"
    if not f.exists():
        raise HTTPException(404, "index.html کنار app.py پیدا نشد.")
    return FileResponse(f)


@app.get("/{name}", include_in_schema=False)
def public_file(name: str):
    if name in _PUBLIC_FILES and (BASE_DIR / name).exists():
        return FileResponse(BASE_DIR / name)
    raise HTTPException(404, "Not found")