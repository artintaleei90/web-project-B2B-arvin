import os
import sqlite3
import hashlib
import hmac
import secrets
import logging
import base64
import json
import mimetypes
import shutil
import threading
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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator

BASE_DIR = Path(__file__).resolve().parent

# اگر DATA_DIR ست شده باشد (مثلاً روی Render با دیسک پایدار)،
# دیتابیس و آپلودها آنجا ذخیره می‌شوند؛ وگرنه کنار app.py.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR)))

UPLOAD_DIR = DATA_DIR / "uploads" / "registrations"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_UPLOAD_DIR = DATA_DIR / "uploads" / "projects"
PROJECTS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PROJECT_IMAGES = 20
MAX_COMPANY_DOCUMENTS = 20
MAX_PROJECT_ATTACHMENTS = 10
MAX_ACTIVE_PROJECTS = 5

DB_PATH = Path(os.getenv("SANAT_DB", str(DATA_DIR / "sanat_market.db")))
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

# سرو فایل‌های آپلودی (تصاویر پروژه‌ها)
app.mount("/uploads", StaticFiles(directory=str(DATA_DIR / "uploads")), name="uploads")


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

        # ---- migration users ----
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

        # ---- migration projects ----
        proj_cols = {row[1] for row in db.execute("PRAGMA table_info(projects)").fetchall()}
        proj_migrations = {
            "project_type": "ALTER TABLE projects ADD COLUMN project_type TEXT",
            "ownership": "ALTER TABLE projects ADD COLUMN ownership TEXT",
            "city": "ALTER TABLE projects ADD COLUMN city TEXT",
            "duration": "ALTER TABLE projects ADD COLUMN duration TEXT",
            "budget": "ALTER TABLE projects ADD COLUMN budget TEXT",
            "description": "ALTER TABLE projects ADD COLUMN description TEXT DEFAULT ''",
            "images": "ALTER TABLE projects ADD COLUMN images TEXT DEFAULT '[]'",
            "status": "ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'pending'",
            "reject_reason": "ALTER TABLE projects ADD COLUMN reject_reason TEXT",
            "reviewed_at": "ALTER TABLE projects ADD COLUMN reviewed_at TEXT",
        }
        for column, sql in proj_migrations.items():
            if column not in proj_cols:
                db.execute(sql)

        # ---- ایندکس‌های projects: فقط بعد از migration ----
        db.executescript("""
        CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        """)


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


class ProjectIn(BaseModel):
    title: str
    project_type: str
    ownership: str
    city: str
    duration: str = ""
    budget: str = ""
    description: str = ""
    images: list[str] = []

    @field_validator("title", "project_type", "ownership", "city")
    @classmethod
    def required_text(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("این فیلد الزامی است.")
        if len(v) > 200:
            raise ValueError("متن واردشده طولانی است.")
        return v

    @field_validator("duration", "budget")
    @classmethod
    def optional_text(cls, v):
        v = (v or "").strip()
        if len(v) > 200:
            raise ValueError("متن طولانی است.")
        return v

    @field_validator("description")
    @classmethod
    def desc_ok(cls, v):
        v = (v or "").strip()
        if len(v) > 3000:
            raise ValueError("توضیحات حداکثر ۳۰۰۰ کاراکتر.")
        return v

    @field_validator("images")
    @classmethod
    def images_ok(cls, v):
        if len(v) > MAX_PROJECT_ATTACHMENTS:
            raise ValueError(f"حداکثر {MAX_PROJECT_ATTACHMENTS} تصویر مجاز است.")
        return v


def user_public(row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    d["has_pending_description"] = d.pop("description_pending", None) is not None
    return d


def project_public(row) -> dict:
    d = dict(row)
    try:
        d["images"] = json.loads(d.get("images") or "[]")
    except Exception:
        d["images"] = []
    return d


# ---------------------------------------------------------------- telegram
def send_admin_approval(user_id: str, text: str, kind: str = "registration", attachments=None):
    """attachments: لیستی از dict با کلیدهای path و caption"""
    try:
        from telegram_api import send_approval
        send_approval(text[:4000], ADMIN_CHAT_ID, user_id, kind, attachments or [])
    except Exception:
        log.exception("Telegram notification failed")


# ---------------------------------------------------------------- file storage
def save_data_url(data_url: str, sub_dir: str, label: str, index: int = 0,
                  base_dir: Optional[Path] = None) -> str:
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

    root = base_dir if base_dir is not None else UPLOAD_DIR
    folder = root / sub_dir
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{label}_{index}{ext}"
    path = folder / filename
    path.write_bytes(raw)
    return str(path.relative_to(DATA_DIR)).replace("\\", "/")


def save_registration_files(data: RegisterIn, user_id: str):
    attachments = []

    national = save_data_url(data.national_id_image, user_id, "national_id")
    attachments.append({
        "path": national,
        "caption": f"🪪 کارت ملی — {data.first_name} {data.last_name} | کد ملی: {data.national_id}",
    })

    if len(data.project_images) > MAX_PROJECT_IMAGES:
        raise HTTPException(400, f"حداکثر {MAX_PROJECT_IMAGES} تصویر پروژه مجاز است.")
    total_proj = len(data.project_images)
    for i, item in enumerate(data.project_images, 1):
        p = save_data_url(item, user_id, "project_image", i)
        attachments.append({
            "path": p,
            "caption": f"🖼 تصویر پروژه {i} از {total_proj}",
        })

    if len(data.company_documents) > MAX_COMPANY_DOCUMENTS:
        raise HTTPException(400, f"حداکثر {MAX_COMPANY_DOCUMENTS} مدرک شرکت مجاز است.")
    total_doc = len(data.company_documents)
    for i, item in enumerate(data.company_documents, 1):
        p = save_data_url(item, user_id, "company_document", i)
        attachments.append({
            "path": p,
            "caption": f"📎 مدرک شرکت {i} از {total_doc}",
        })

    return attachments


# ---------------------------------------------------------------- telegram listener (in-process)
_telegram_thread: Optional[threading.Thread] = None


def _run_telegram_listener():
    try:
        import check_message
        check_message.check_messages()
    except Exception:
        log.exception("Telegram listener crashed")


@app.on_event("startup")
def _start_telegram_listener():
    global _telegram_thread
    if os.getenv("RUN_TELEGRAM_LISTENER", "1") != "1":
        log.info("Telegram listener disabled (RUN_TELEGRAM_LISTENER != 1)")
        return
    if _telegram_thread and _telegram_thread.is_alive():
        log.info("Telegram listener already running")
        return
    _telegram_thread = threading.Thread(
        target=_run_telegram_listener,
        name="telegram-listener",
        daemon=True,
    )
    _telegram_thread.start()
    log.info("Telegram listener thread started")


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

    attachments = save_registration_files(data, user_id)
    national_id_path = attachments[0]["path"]
    project_count = len(data.project_images)
    company_count = len(data.company_documents)

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
                 json.dumps([a["path"] for a in attachments if "project_image" in a["path"]], ensure_ascii=False),
                 company, company_id, role,
                 json.dumps([a["path"] for a in attachments if "company_document" in a["path"]], ensure_ascii=False),
                 "pending", registration_time,
                 registration_ip, registration_time, device_browser, request_id),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "این Gmail یا شماره تماس قبلاً ثبت شده است.")
    except Exception:
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
📎 تصاویر پروژه: {project_count} فایل
📎 مدارک شرکت: {company_count} فایل

🔐 اطلاعات خودکار سیستم:
🌐 IP ثبت‌نام: {registration_ip}
🕒 زمان ثبت: {registration_time}
💻 مرورگر/دستگاه: {device_browser[:500]}
🆔 شناسه کاربر: {user_id}
🧾 شناسه درخواست: {request_id}

⏳ وضعیت: در انتظار بررسی ادمین"""

    background.add_task(send_admin_approval, user_id, message, "registration", attachments)

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
        projects = [project_public(x) for x in db.execute(
            "SELECT * FROM projects WHERE user_id=? ORDER BY created_at DESC",
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


# ================================================================
#                        PROJECTS
# ================================================================
@app.post("/api/projects")
def create_project(data: ProjectIn, background: BackgroundTasks,
                   user=Depends(current_user)):
    if user["status"] != "approved":
        raise HTTPException(403, "حساب شما هنوز تأیید نشده است.")

    with get_db() as db:
        active = db.execute(
            "SELECT COUNT(*) AS c FROM projects WHERE user_id=? AND status='pending'",
            (user["id"],),
        ).fetchone()["c"]
    if active >= MAX_ACTIVE_PROJECTS:
        raise HTTPException(
            429,
            f"حداکثر {MAX_ACTIVE_PROJECTS} پروژه در حال بررسی می‌توانید داشته باشید. "
            "تا تعیین وضعیت پروژه‌های قبلی صبر کنید.",
        )

    project_id = secrets.token_hex(16)

    image_paths = []
    if len(data.images) > MAX_PROJECT_ATTACHMENTS:
        raise HTTPException(400, f"حداکثر {MAX_PROJECT_ATTACHMENTS} تصویر مجاز است.")
    for i, item in enumerate(data.images, 1):
        p = save_data_url(item, user["id"], "project_image", i,
                          base_dir=PROJECTS_UPLOAD_DIR)
        image_paths.append(p)

    created_at = now_iso()

    try:
        with get_db() as db:
            db.execute(
                """INSERT INTO projects
                   (id,user_id,title,project_type,ownership,city,duration,budget,
                    description,images,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (project_id, user["id"], data.title, data.project_type,
                 data.ownership, data.city, data.duration, data.budget,
                 data.description, json.dumps(image_paths, ensure_ascii=False),
                 "pending", created_at),
            )
    except Exception:
        shutil.rmtree(PROJECTS_UPLOAD_DIR / user["id"], ignore_errors=True)
        raise

    role_text = {"employer": "کارفرما", "contractor": "پیمانکار"}.get(
        user["role"], "ثبت نشده")
    message = f"""🆕 پروژه جدید در انتظار تأیید

👤 کاربر: {user['first_name']} {user['last_name']}
📧 {user['email']}
📱 {user['phone']}
👷 نقش: {role_text}

📌 عنوان پروژه: {data.title}
🏷 نوع پروژه: {data.project_type}
🏢 دستمزد/مالکیت: {data.ownership}
📍 شهر: {data.city}
⏱ مدت زمان: {data.duration or '—'}
💰 بودجه: {data.budget or '—'}
📝 توضیحات: {data.description[:1500] or '—'}

🖼 تعداد تصاویر: {len(image_paths)}
🆔 شناسه پروژه: {project_id}"""

    attachments = [
        {"path": p, "caption": f"🖼 تصویر پروژه {i} از {len(image_paths)}"}
        for i, p in enumerate(image_paths, 1)
    ]
    background.add_task(
        send_admin_approval, project_id, message, "project", attachments,
    )

    return {
        "message": "پروژه ثبت شد و در انتظار تأیید ادمین است.",
        "project_id": project_id,
    }


@app.get("/api/projects/mine")
def my_projects(user=Depends(current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM projects WHERE user_id=? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    return {"projects": [project_public(r) for r in rows]}


@app.get("/api/projects")
def public_projects(limit: int = 50, offset: int = 0):
    with get_db() as db:
        rows = db.execute(
            """SELECT p.*, u.first_name, u.last_name, u.company_name
               FROM projects p JOIN users u ON u.id = p.user_id
               WHERE p.status='approved'
               ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
    return {"projects": [project_public(r) for r in rows]}


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