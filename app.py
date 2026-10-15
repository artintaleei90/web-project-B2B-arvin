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
from pydantic import BaseModel, EmailStr, Field, field_validator

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
            request_id TEXT,
            profile_pending_json TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_active
            ON users(email) WHERE status != 'rejected';
        CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            need TEXT NOT NULL,
            city TEXT NOT NULL,
            budget TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            image_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_projects_status_created
            ON projects(status, created_at);

        CREATE TABLE IF NOT EXISTS project_requests (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            contractor_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            proposed_duration TEXT NOT NULL DEFAULT '',
            proposed_price TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            decided_at TEXT,
            UNIQUE(project_id, contractor_id)
        );
        CREATE INDEX IF NOT EXISTS idx_project_requests_project
            ON project_requests(project_id, status);

        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            project_id TEXT,
            request_id TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(user_id, is_read, created_at);

        CREATE TABLE IF NOT EXISTS project_chat_messages (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_chat_request ON project_chat_messages(request_id, created_at);

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

        # ---- migrations: users ----
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
            "profile_pending_json": "ALTER TABLE users ADD COLUMN profile_pending_json TEXT",
        }
        for column, sql in migrations.items():
            if column not in existing:
                db.execute(sql)

        # ---- migrations: projects ----
        existing_projects = {row[1] for row in db.execute("PRAGMA table_info(projects)").fetchall()}
        project_migrations = {
            "budget": "ALTER TABLE projects ADD COLUMN budget TEXT NOT NULL DEFAULT ''",
        }
        for column, sql in project_migrations.items():
            if column not in existing_projects:
                db.execute(sql)

        existing_requests = {row[1] for row in db.execute("PRAGMA table_info(project_requests)").fetchall()}
        request_migrations = {
            "proposed_duration": "ALTER TABLE project_requests ADD COLUMN proposed_duration TEXT NOT NULL DEFAULT ''",
            "proposed_price": "ALTER TABLE project_requests ADD COLUMN proposed_price TEXT NOT NULL DEFAULT ''",
        }
        for column, sql in request_migrations.items():
            if column not in existing_requests:
                db.execute(sql)


init_db()


# ---------------- security ----------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 210_000
        )
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
        (
            _token_hash(token),
            user_id,
            now.isoformat(),
            (now + timedelta(days=SESSION_DAYS)).isoformat(),
        ),
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


def require_approved(user):
    if user["status"] != "approved":
        raise HTTPException(
            403,
            "حساب شما هنوز توسط ادمین تأیید نشده است. پس از تأیید می‌توانید از این بخش استفاده کنید.",
        )


def require_role(user, role: str):
    require_approved(user)
    if user["role"] != role:
        raise HTTPException(403, "این بخش برای حساب شما در دسترس نیست.")


# ---------------- validation ----------------
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
    project_images: list[str] = Field(default_factory=list)
    company_name: Optional[str] = None
    company_id: Optional[str] = None
    role: str
    company_documents: list[str] = Field(default_factory=list)

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
        return v.strip()

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
        return v.strip()


class ProjectIn(BaseModel):
    title: str
    need: str
    city: str
    budget: str = ""
    details: str = ""
    image: Optional[str] = None

    @field_validator("title", "need", "city")
    @classmethod
    def project_required(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("این فیلد الزامی است.")
        if len(v) > 300:
            raise ValueError("متن واردشده بیش از حد طولانی است.")
        return v

    @field_validator("budget")
    @classmethod
    def budget_ok(cls, v):
        v = (v or "").strip()
        if len(v) > 100:
            raise ValueError("مقدار بودجه بیش از حد طولانی است.")
        return v

    @field_validator("details")
    @classmethod
    def details_ok(cls, v):
        v = v.strip()
        if len(v) > 10000:
            raise ValueError("جزئیات پروژه بیش از حد طولانی است.")
        return v


class RequestProjectIn(BaseModel):
    project_id: str = ""
    proposed_duration: str = "قابل مذاکره از طریق سامانه"
    proposed_price: str = "پس از بررسی پروژه اعلام می‌شود"

    @field_validator("proposed_duration", "proposed_price")
    @classmethod
    def request_text_ok(cls, v):
        v = (v or "").strip()
        if len(v) > 200:
            raise ValueError("مقدار واردشده بیش از حد طولانی است.")
        return v or "ثبت نشده"


# ---------------- public serialization ----------------
def user_public(row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    d["has_pending_description"] = d.pop("description_pending", None) is not None
    pending_profile = d.pop("profile_pending_json", None)
    d["has_pending_profile"] = pending_profile is not None
    return d


def public_project(row) -> dict:
    d = dict(row)
    owner_id = d.pop("user_id", None)
    d["owner_id"] = owner_id
    d["budget"] = d.get("budget") or ""
    d["image_url"] = f"/uploads/{d['image_path']}" if d.get("image_path") else None
    return d


# ---------------- telegram ----------------
def send_admin_approval(
    item_id: str,
    text: str,
    kind: str = "registration",
    attachments=None,
):
    try:
        from telegram_api import send_approval
        send_approval(
            text[:4000],
            ADMIN_CHAT_ID,
            item_id,
            kind,
            attachments or [],
        )
    except Exception:
        log.exception("Telegram notification failed")


# ---------------- file storage ----------------
def save_data_url(data_url: str, owner_id: str, label: str, index: int = 0) -> str:
    if not isinstance(data_url, str) or not data_url.startswith("data:"):
        raise HTTPException(400, "فرمت فایل ارسال‌شده معتبر نیست.")
    try:
        header, encoded = data_url.split(",", 1)
        mime = header[5:].split(";", 1)[0].lower()
        if not mime.startswith("image/") and label in {
            "national_id",
            "project_image",
            "project_main",
        }:
            raise HTTPException(400, "فایل تصویر باید از نوع تصویری باشد.")
        if label == "company_document" and not (
            mime.startswith("image/") or mime == "application/pdf"
        ):
            raise HTTPException(400, "مدرک شرکت باید تصویر یا PDF باشد.")
        raw = base64.b64decode(encoded, validate=True)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "فایل ارسال‌شده قابل خواندن نیست.")

    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(413, "حجم هر فایل نباید بیشتر از ۱۰ مگابایت باشد.")

    ext = mimetypes.guess_extension(mime) or ".bin"
    if mime == "image/jpeg":
        ext = ".jpg"
    elif mime == "image/png":
        ext = ".png"
    elif mime == "image/webp":
        ext = ".webp"
    elif mime == "application/pdf":
        ext = ".pdf"

    folder = UPLOAD_DIR / owner_id
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{label}_{index}{ext}"
    path = folder / filename
    path.write_bytes(raw)
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def save_registration_files(data: RegisterIn, user_id: str):
    attachments = []

    national = save_data_url(
        data.national_id_image, user_id, "national_id"
    )
    attachments.append(
        {
            "path": national,
            "caption": f"🪪 کارت ملی — {data.first_name} {data.last_name} | کد ملی: {data.national_id}",
        }
    )

    if len(data.project_images) > MAX_PROJECT_IMAGES:
        raise HTTPException(
            400, f"حداکثر {MAX_PROJECT_IMAGES} تصویر پروژه مجاز است."
        )
    total_proj = len(data.project_images)
    for i, item in enumerate(data.project_images, 1):
        p = save_data_url(item, user_id, "project_image", i)
        attachments.append(
            {"path": p, "caption": f"🖼 تصویر نمونه پروژه {i} از {total_proj}"}
        )

    if len(data.company_documents) > MAX_COMPANY_DOCUMENTS:
        raise HTTPException(
            400, f"حداکثر {MAX_COMPANY_DOCUMENTS} مدرک شرکت مجاز است."
        )
    total_doc = len(data.company_documents)
    for i, item in enumerate(data.company_documents, 1):
        p = save_data_url(item, user_id, "company_document", i)
        attachments.append(
            {"path": p, "caption": f"📎 مدرک شرکت {i} از {total_doc}"}
        )

    return attachments


# ---------------- auth routes ----------------
@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/register")
def register(
    data: RegisterIn, request: Request, background: BackgroundTasks
):
    email = str(data.email).lower().strip()
    phone = data.phone
    company = (data.company_name or "").strip() or None
    company_id = (data.company_id or "").strip() or None
    role = (data.role or "").strip() or None
    description = data.description.strip()

    if role not in ("employer", "contractor"):
        raise HTTPException(
            400, "نوع فعالیت الزامی است و باید کارفرما یا پیمانکار باشد."
        )
    if company and not company_id:
        raise HTTPException(
            400, "در صورت ثبت شرکت، شناسه شرکت الزامی است."
        )
    if not company and data.company_documents:
        raise HTTPException(
            400, "برای ارسال مدارک شرکت، ابتدا نام شرکت را ثبت کنید."
        )

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

    try:
        with get_db() as db:
            rows = db.execute(
                "SELECT status, rejected_at FROM users WHERE lower(email)=? OR phone=?",
                (email, phone),
            ).fetchall()

            for r in rows:
                if r["status"] != "rejected":
                    raise HTTPException(
                        409, "این Gmail یا شماره تماس قبلاً ثبت شده است."
                    )
                if r["rejected_at"]:
                    rejected_at = datetime.fromisoformat(r["rejected_at"])
                    if (
                        datetime.now(timezone.utc) - rejected_at
                        < REJECT_COOLDOWN
                    ):
                        raise HTTPException(
                            409,
                            "این حساب رد شده است. ثبت‌نام مجدد تا ۵ روز امکان‌پذیر نیست.",
                        )

            db.execute(
                """INSERT INTO users
                   (id,first_name,last_name,national_id,birth_date,gender,phone,email,password_hash,
                    activity_city,activity_field,work_history,description,national_id_image,project_samples,
                    project_images,company_name,company_id,role,company_documents,status,created_at,
                    registration_ip,registration_time,device_browser,request_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    user_id,
                    data.first_name,
                    data.last_name,
                    data.national_id,
                    data.birth_date,
                    data.gender,
                    phone,
                    email,
                    hash_password(data.password),
                    data.activity_city,
                    data.activity_field,
                    data.work_history.strip(),
                    description,
                    national_id_path,
                    data.project_samples.strip(),
                    json.dumps(
                        [
                            a["path"]
                            for a in attachments
                            if "project_image" in a["path"]
                        ],
                        ensure_ascii=False,
                    ),
                    company,
                    company_id,
                    role,
                    json.dumps(
                        [
                            a["path"]
                            for a in attachments
                            if "company_document" in a["path"]
                        ],
                        ensure_ascii=False,
                    ),
                    "pending",
                    registration_time,
                    registration_ip,
                    registration_time,
                    device_browser,
                    request_id,
                ),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(
            409, "این Gmail یا شماره تماس قبلاً ثبت شده است."
        )
    except Exception:
        import shutil
        shutil.rmtree(UPLOAD_DIR / user_id, ignore_errors=True)
        raise

    role_text = {
        "employer": "کارفرما",
        "contractor": "پیمانکار",
    }.get(role, "ثبت نشده")

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

🔐 اطلاعات خودکار سیستم:
🌐 IP ثبت‌نام: {registration_ip}
🕒 زمان ثبت: {registration_time}
💻 مرورگر/دستگاه: {device_browser[:500]}
🆔 شناسه کاربر: {user_id}
🧾 شناسه درخواست: {request_id}

⏳ وضعیت: در انتظار بررسی ادمین"""

    background.add_task(
        send_admin_approval,
        user_id,
        message,
        "registration",
        attachments[:1],
    )

    with get_db() as db:
        token = create_session(db, user_id)
        row = db.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone()

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
            "SELECT * FROM users WHERE lower(email)=? ORDER BY created_at DESC LIMIT 1",
            (email,),
        ).fetchone()
        ok = verify_password(
            data.password, row["password_hash"] if row else _DUMMY_HASH
        )
        if not row or not ok:
            raise HTTPException(401, "Gmail یا رمز عبور اشتباه است.")
        token = create_session(db, row["id"])
    return {"user": user_public(row), "token": token}


@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    token = _bearer(authorization)
    with get_db() as db:
        db.execute(
            "DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),)
        )
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"user": user_public(user)}


# ---------------- profile ----------------
@app.get("/api/profile")
def profile(user=Depends(current_user)):
    with get_db() as db:
        projects = [
            dict(x)
            for x in db.execute(
                """SELECT id,title,need,city,budget,details,image_path,status,created_at,
                          approved_at,deleted_at
                   FROM projects WHERE user_id=? ORDER BY created_at DESC""",
                (user["id"],),
            )
        ]
        for p in projects:
            p["image_url"] = (
                f"/uploads/{p['image_path']}" if p.get("image_path") else None
            )

        reviews = [
            dict(x)
            for x in db.execute(
                "SELECT employer_name,text,created_at FROM reviews WHERE user_id=? ORDER BY created_at DESC",
                (user["id"],),
            )
        ]

    return {
        "user": user_public(user),
        "projects": projects,
        "reviews": reviews,
    }


@app.put("/api/profile/description")
def update_description(
    data: DescriptionIn,
    background: BackgroundTasks,
    user=Depends(current_user),
):
    require_approved(user)

    new_desc = data.description.strip()
    with get_db() as db:
        db.execute(
            "UPDATE users SET description_pending=? WHERE id=?",
            (new_desc, user["id"]),
        )

    message = f"""✏️ درخواست تغییر توضیحات پروفایل

🆔 شناسه کاربر:
{user["id"]}

👤 {user["first_name"]} {user["last_name"]}
📧 {user["email"]}

📝 توضیحات جدید:
{new_desc[:1500] or "(خالی)"}"""

    background.add_task(
        send_admin_approval,
        user["id"],
        message,
        "description",
        [],
    )
    return {
        "message": "توضیحات برای بررسی ادمین ارسال شد. تا تأیید، حساب شما قفل نمی‌شود."
    }


class ProfileEditIn(BaseModel):
    first_name: str
    last_name: str
    birth_date: str
    gender: str
    phone: str
    activity_city: str
    activity_field: str
    work_history: str = ""
    description: str = ""
    company_name: Optional[str] = None
    company_id: Optional[str] = None
    role: str

    @field_validator("first_name", "last_name")
    @classmethod
    def profile_name_ok(cls, v):
        v = v.strip()
        if not v or len(v) > 60:
            raise ValueError("نام و نام خانوادگی الزامی است.")
        return v

    @field_validator("phone")
    @classmethod
    def profile_phone_ok(cls, v):
        return validate_iran_phone(v)

    @field_validator("birth_date", "gender", "activity_city", "activity_field", "role")
    @classmethod
    def profile_required_ok(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("این فیلد الزامی است.")
        return v

    @field_validator("description")
    @classmethod
    def profile_desc_ok(cls, v):
        v = (v or "").strip()
        if len(v) > 2000:
            raise ValueError("توضیحات حداکثر ۲۰۰۰ کاراکتر می‌تواند باشد.")
        return v

    @field_validator("work_history")
    @classmethod
    def profile_history_ok(cls, v):
        v = (v or "").strip()
        if len(v) > 10000:
            raise ValueError("سابقه کاری بیش از حد طولانی است.")
        return v


@app.put("/api/profile")
def update_profile(
    data: ProfileEditIn,
    background: BackgroundTasks,
    user=Depends(current_user),
):
    require_approved(user)

    company = (data.company_name or "").strip() or None
    company_id = (data.company_id or "").strip() or None
    if company and not company_id:
        raise HTTPException(400, "در صورت ثبت شرکت، شناسه شرکت الزامی است.")
    if not company:
        company_id = None
    if data.role not in ("employer", "contractor"):
        raise HTTPException(400, "نوع فعالیت باید کارفرما یا پیمانکار باشد.")

    with get_db() as db:
        duplicate = db.execute(
            """SELECT id FROM users
               WHERE phone=? AND id<>? AND status!='rejected'""",
            (data.phone.strip(), user["id"]),
        ).fetchone()
        if duplicate:
            raise HTTPException(409, "این شماره تماس قبلاً برای حساب دیگری ثبت شده است.")

    pending = {
        "first_name": data.first_name.strip(),
        "last_name": data.last_name.strip(),
        "birth_date": data.birth_date.strip(),
        "gender": data.gender.strip(),
        "phone": data.phone.strip(),
        "activity_city": data.activity_city.strip(),
        "activity_field": data.activity_field.strip(),
        "work_history": data.work_history.strip(),
        "description": data.description.strip(),
        "company_name": company,
        "company_id": company_id,
        "role": data.role.strip(),
    }

    with get_db() as db:
        db.execute(
            "UPDATE users SET profile_pending_json=?, status='pending' WHERE id=?",
            (json.dumps(pending, ensure_ascii=False), user["id"]),
        )

    role_text = {"employer": "کارفرما", "contractor": "پیمانکار"}.get(data.role, data.role)
    message = f"""✏️ درخواست ویرایش پروفایل صنعت مارکت

🆔 شناسه کاربر: {user["id"]}
👤 نام فعلی: {user["first_name"]} {user["last_name"]}
📧 Gmail: {user["email"]}

📝 اطلاعات جدید:
نام: {pending["first_name"]} {pending["last_name"]}
تاریخ تولد: {pending["birth_date"]}
جنسیت: {pending["gender"]}
شماره تماس: {pending["phone"]}
شهر فعالیت: {pending["activity_city"]}
حوزه فعالیت: {pending["activity_field"]}
سابقه کاری: {pending["work_history"][:1200] or "ثبت نشده"}
توضیحات: {pending["description"][:1200] or "ثبت نشده"}
شرکت: {pending["company_name"] or "ندارد"}
شناسه شرکت: {pending["company_id"] or "—"}
نوع فعالیت: {role_text}

⏳ وضعیت: در انتظار تأیید ادمین"""

    background.add_task(
        send_admin_approval,
        user["id"],
        message,
        "profile",
        [],
    )

    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

    return {
        "message": "ویرایش پروفایل برای تأیید ادمین ارسال شد. تا زمان تأیید، حساب شما در حال بررسی است.",
        "user": user_public(row),
    }

# ---------------- projects ----------------
@app.post("/api/projects")
def create_project(
    data: ProjectIn,
    request: Request,
    background: BackgroundTasks,
    user=Depends(current_user),
):
    require_role(user, "employer")

    project_id = secrets.token_hex(16)
    image_path = None

    if data.image:
        image_path = save_data_url(
            data.image, user["id"], "project_main", 1
        )

    created = now_iso()
    with get_db() as db:
        db.execute(
            """INSERT INTO projects
               (id,user_id,title,need,city,budget,details,image_path,status,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                project_id,
                user["id"],
                data.title,
                data.need,
                data.city,
                data.budget,
                data.details,
                image_path,
                "pending",
                created,
            ),
        )

    message = f"""🆕 درخواست ثبت پروژه جدید صنعت مارکت

📌 عنوان پروژه: {data.title}
🛠 نیاز پروژه: {data.need}
📍 شهر: {data.city}
💰 حداکثر بودجه: {data.budget or "ثبت نشده"}
📝 جزئیات:
{data.details[:2500] or "ثبت نشده"}

👤 کارفرما: {user["first_name"]} {user["last_name"]}
📱 شماره: {user["phone"]}
📧 Gmail: {user["email"]}
🏢 شرکت: {user["company_name"] or "ندارد"}
🆔 شناسه پروژه: {project_id}
🕒 زمان ثبت: {created}

⏳ وضعیت: در انتظار بررسی ادمین"""

    attachments = []
    if image_path:
        attachments.append(
            {
                "path": image_path,
                "caption": f"🖼 تصویر پروژه — {data.title}",
            }
        )

    background.add_task(
        send_admin_approval,
        project_id,
        message,
        "project",
        attachments,
    )

    return {
        "message": "پروژه ثبت شد و برای بررسی ادمین ارسال شد.",
        "project": {
            "id": project_id,
            "title": data.title,
            "need": data.need,
            "city": data.city,
            "budget": data.budget,
            "details": data.details,
            "status": "pending",
            "image_url": f"/uploads/{image_path}" if image_path else None,
            "created_at": created,
        },
    }


@app.get("/api/projects")
def list_projects(
    q: str = "",
    city: str = "",
):
    q = q.strip().lower()
    city = city.strip()

    sql = """
        SELECT p.*, u.first_name AS owner_first_name, u.last_name AS owner_last_name
        FROM projects p
        JOIN users u ON u.id=p.user_id
        WHERE p.status='active' AND u.status='approved'
    """
    params = []

    if q:
        sql += " AND (lower(p.title) LIKE ? OR lower(p.need) LIKE ? OR lower(p.details) LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    if city:
        sql += " AND p.city=?"
        params.append(city)

    sql += " ORDER BY p.approved_at DESC, p.created_at DESC"

    with get_db() as db:
        rows = db.execute(sql, params).fetchall()

    return {
        "projects": [
            {
                **public_project(row),
                "owner_name": f"{row['owner_first_name']} {row['owner_last_name']}",
            }
            for row in rows
        ]
    }


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    with get_db() as db:
        row = db.execute(
            """SELECT p.*, u.first_name AS owner_first_name,
                      u.last_name AS owner_last_name
               FROM projects p JOIN users u ON u.id=p.user_id
               WHERE p.id=?""",
            (project_id,),
        ).fetchone()

    if not row or row["status"] != "active":
        raise HTTPException(404, "پروژه پیدا نشد.")

    d = public_project(row)
    d["owner_name"] = f"{row['owner_first_name']} {row['owner_last_name']}"
    return {"project": d}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str, user=Depends(current_user)):
    require_role(user, "employer")

    with get_db() as db:
        project = db.execute(
            "SELECT * FROM projects WHERE id=? AND user_id=?",
            (project_id, user["id"]),
        ).fetchone()

        if not project:
            raise HTTPException(404, "پروژه پیدا نشد.")
        if project["status"] == "deleted":
            raise HTTPException(400, "این پروژه قبلاً حذف شده است.")

        db.execute(
            "UPDATE projects SET status='deleted', deleted_at=? WHERE id=?",
            (now_iso(), project_id),
        )

    return {"message": "پروژه حذف شد."}


# ---------------- contractor requests + bell ----------------
@app.post("/api/projects/{project_id}/request")
def request_project(
    project_id: str,
    data: RequestProjectIn,
    user=Depends(current_user),
):
    require_role(user, "contractor")

    with get_db() as db:
        project = db.execute(
            """SELECT * FROM projects
               WHERE id=? AND status='active'""",
            (project_id,),
        ).fetchone()

        if not project:
            raise HTTPException(404, "پروژه فعال پیدا نشد.")
        if project["user_id"] == user["id"]:
            raise HTTPException(400, "نمی‌توانید برای پروژه خودتان درخواست بدهید.")

        existing = db.execute(
            """SELECT id,status FROM project_requests
               WHERE project_id=? AND contractor_id=?""",
            (project_id, user["id"]),
        ).fetchone()

        if existing:
            raise HTTPException(409, "شما قبلاً برای این پروژه درخواست داده‌اید.")

        active_count = db.execute(
            "SELECT COUNT(*) FROM project_requests WHERE contractor_id=? AND status IN ('pending','accepted')",
            (user["id"],),
        ).fetchone()[0]
        if active_count >= 5:
            raise HTTPException(400, "حداکثر می‌توانید هم‌زمان برای ۵ پروژه درخواست فعال داشته باشید. ابتدا یکی از درخواست‌ها را حذف کنید.")

        request_id = secrets.token_hex(16)
        created = now_iso()

        db.execute(
            """INSERT INTO project_requests
               (id,project_id,contractor_id,status,proposed_duration,proposed_price,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                request_id,
                project_id,
                user["id"],
                "pending",
                data.proposed_duration,
                data.proposed_price,
                created,
            ),
        )

        db.execute(
            """INSERT INTO notifications
               (id,user_id,kind,project_id,request_id,is_read,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                secrets.token_hex(16),
                project["user_id"],
                "project_request",
                project_id,
                request_id,
                0,
                created,
            ),
        )

    return {"message": "درخواست شما برای کارفرما ارسال شد."}

@app.get("/api/notifications")
def notifications(user=Depends(current_user)):
    require_approved(user)

    with get_db() as db:
        rows = db.execute(
            """SELECT n.*, p.title AS project_title, p.need AS project_need,
                      u.id AS applicant_id,
                      u.first_name AS applicant_first_name,
                      u.last_name AS applicant_last_name,
                      u.company_name AS applicant_company,
                      u.company_id AS applicant_company_id,
                      u.activity_city AS applicant_city,
                      u.activity_field AS applicant_field,
                      u.work_history AS applicant_work_history,
                      u.description AS applicant_description,
                      r.status AS request_status
               FROM notifications n
               LEFT JOIN projects p ON p.id=n.project_id
               LEFT JOIN project_requests r ON r.id=n.request_id
               LEFT JOIN users u ON u.id=r.contractor_id
               WHERE n.user_id=?
               ORDER BY n.created_at DESC
               LIMIT 100""",
            (user["id"],),
        ).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        d["is_read"] = bool(d["is_read"])
        result.append(d)

    return {
        "notifications": result,
        "unread": sum(1 for x in result if not x["is_read"]),
    }


@app.post("/api/notifications/read")
def mark_notifications_read(user=Depends(current_user)):
    require_approved(user)
    with get_db() as db:
        db.execute(
            "UPDATE notifications SET is_read=1 WHERE user_id=?",
            (user["id"],),
        )
    return {"ok": True}


@app.post("/api/project-requests/{request_id}/choose")
def choose_project_request(
    request_id: str,
    user=Depends(current_user),
):
    require_role(user, "employer")

    with get_db() as db:
        req = db.execute(
            """SELECT r.*, p.user_id AS employer_id
               FROM project_requests r
               JOIN projects p ON p.id=r.project_id
               WHERE r.id=?""",
            (request_id,),
        ).fetchone()

        if not req:
            raise HTTPException(404, "درخواست پیدا نشد.")
        if req["employer_id"] != user["id"]:
            raise HTTPException(403, "این درخواست متعلق به پروژه شما نیست.")
        if req["status"] != "pending":
            raise HTTPException(400, "این درخواست قبلاً بررسی شده است.")

        db.execute(
            """UPDATE project_requests
               SET status='accepted', decided_at=?
               WHERE id=?""",
            (now_iso(), request_id),
        )

        db.execute(
            """UPDATE project_requests
               SET status='rejected', decided_at=?
               WHERE project_id=? AND id<>? AND status='pending'""",
            (now_iso(), req["project_id"], request_id),
        )

        db.execute(
            """INSERT INTO notifications
               (id,user_id,kind,project_id,request_id,is_read,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                secrets.token_hex(16),
                req["contractor_id"],
                "request_accepted",
                req["project_id"],
                request_id,
                0,
                now_iso(),
            ),
        )

    return {"message": "پیمانکار انتخاب شد و درخواست‌های دیگر بسته شدند."}


# ---------------- private project workspace + contact-safe chat ----------------
import re

CONTACT_PATTERNS = [
    # Emails, URLs, common social handles and phone numbers written with digits.
    re.compile(r"[A-Z0-9._%+-]+\s*@\s*[A-Z0-9.-]+\s*\.\s*[A-Z]{2,}", re.I),
    re.compile(r"(?:https?://|www\.)\S+", re.I),
    re.compile(r"(?:\+?98|0098|0)\s*9(?:[\s\-().]*[0-9۰-۹٠-٩]){9}"),
    re.compile(r"(?:telegram|تلگرام|واتساپ|whatsapp|اینستاگرام|instagram|ایتا|بله|روبیکا|سروش|گپ)\s*[:：@]?\s*[@\w.-]+", re.I),
    re.compile(r"@\w{3,}"),
    # Email addresses shared as words, e.g. "name at gmail dot com".
    re.compile(r"(?:gmail|جیمیل|yahoo|یاهو|outlook|hotmail|ایمیل|email)\b|(?:\bat\b|اَت|اَت‌ساین|علامتِ? ات|دات|dot)\s*(?:com|net|org|ir|کام|نت|آی‌آر)?", re.I),
]

# Common number words. We reject long sequences of these words so that writing a
# phone number as "صفر نهصد و ..." is not an easy bypass. This is intentionally
# conservative: long number-word sequences may need rewriting even when benign.
_NUMBER_WORDS = set("صفر یک یه دو سه چهار پنج شش هفت هشت نه ده یازده دوازده سیزده چهارده پانزده شانزده هفده هجده نوزده بیست سی چهل پنجاه شصت هفتاد هشتاد نود صد دویست سیصد چهارصد پانصد ششصد هفتصد هشتصد نهصد thousand hundred zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred".split())

def contains_spelled_number_sequence(text: str) -> bool:
    normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")).lower()
    # Remove punctuation between tokens while preserving word boundaries.
    words = re.findall(r"[a-z]+|[آ-ی]+|\d+", normalized)
    run = 0
    for word in words:
        if word in _NUMBER_WORDS:
            run += 1
            if run >= 7:
                return True
        elif word in {"و", "and", "-"} and run:
            continue
        else:
            run = 0
    # A mix of numeric digits and number words is also suspicious.
    number_tokens = sum(1 for word in words if word in _NUMBER_WORDS or word.isdigit())
    return number_tokens >= 8

def ensure_request_party(db, request_id, user_id):
    row = db.execute("""SELECT r.*, p.user_id AS employer_id, p.title AS project_title
        FROM project_requests r JOIN projects p ON p.id=r.project_id WHERE r.id=?""", (request_id,)).fetchone()
    if not row:
        raise HTTPException(404, "درخواست پیدا نشد.")
    if user_id not in (row["employer_id"], row["contractor_id"]):
        raise HTTPException(403, "به این گفتگو دسترسی ندارید.")
    if row["status"] != "accepted":
        raise HTTPException(403, "گفتگو پس از انتخاب پیمانکار توسط کارفرما فعال می‌شود.")
    return row

def safe_profile(db, uid):
    row = db.execute("""SELECT id, first_name, last_name, role, company_name, description,
        activity_city, activity_field, work_history, project_samples, project_images
        FROM users WHERE id=? AND status='approved'""", (uid,)).fetchone()
    if not row:
        raise HTTPException(404, "پروفایل پیدا نشد.")
    d = dict(row)
    # Deliberately omit phone, email, national ID, birth date and private documents.
    return d

@app.get("/api/employer/my-projects")
def employer_my_projects(user=Depends(current_user)):
    require_role(user, "employer")
    with get_db() as db:
        projects = db.execute("SELECT * FROM projects WHERE user_id=? AND status!='deleted' ORDER BY created_at DESC", (user["id"],)).fetchall()
        result=[]
        for p in projects:
            item=public_project(p)
            item["request_count"] = db.execute("SELECT COUNT(*) FROM project_requests WHERE project_id=? AND status IN ('pending','accepted')", (p["id"],)).fetchone()[0]
            result.append(item)
    return {"projects": result}

@app.get("/api/employer/projects/{project_id}/requests")
def employer_project_requests(project_id: str, user=Depends(current_user)):
    require_role(user, "employer")
    with get_db() as db:
        p=db.execute("SELECT id,title,user_id FROM projects WHERE id=?", (project_id,)).fetchone()
        if not p: raise HTTPException(404, "پروژه پیدا نشد.")
        if p["user_id"] != user["id"]: raise HTTPException(403, "این پروژه متعلق به شما نیست.")
        rows=db.execute("""SELECT r.id AS request_id,r.status,r.proposed_duration,r.proposed_price,r.created_at,
            u.id AS contractor_id,u.first_name,u.last_name,u.role,u.company_name,u.description,
            u.activity_city,u.activity_field,u.work_history,u.project_samples,u.project_images
            FROM project_requests r JOIN users u ON u.id=r.contractor_id
            WHERE r.project_id=? ORDER BY CASE r.status WHEN 'accepted' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, r.created_at DESC""", (project_id,)).fetchall()
    return {"project":{"id":p["id"],"title":p["title"]},"requests":[dict(x) for x in rows]}

@app.get("/api/contractor/my-requests")
def contractor_my_requests(user=Depends(current_user)):
    require_role(user, "contractor")
    with get_db() as db:
        rows=db.execute("""SELECT r.id AS request_id,r.status,r.proposed_duration,r.proposed_price,r.created_at,
            p.id AS project_id,p.title,p.need,p.city,p.budget,p.details,p.status AS project_status
            FROM project_requests r JOIN projects p ON p.id=r.project_id
            WHERE r.contractor_id=? ORDER BY r.created_at DESC""", (user["id"],)).fetchall()
        active=db.execute("SELECT COUNT(*) FROM project_requests WHERE contractor_id=? AND status IN ('pending','accepted')", (user["id"],)).fetchone()[0]
    return {"requests":[dict(x) for x in rows],"active_count":active,"active_limit":5}

@app.delete("/api/project-requests/{request_id}")
def delete_own_request(request_id: str, user=Depends(current_user)):
    require_role(user, "contractor")
    with get_db() as db:
        row=db.execute("SELECT * FROM project_requests WHERE id=? AND contractor_id=?", (request_id,user["id"])).fetchone()
        if not row: raise HTTPException(404,"درخواست پیدا نشد.")
        if row["status"] == "accepted": raise HTTPException(400,"درخواست انتخاب‌شده را نمی‌توان حذف کرد؛ ابتدا از پشتیبانی سامانه کمک بگیرید.")
        db.execute("DELETE FROM project_chat_messages WHERE request_id=?", (request_id,))
        db.execute("DELETE FROM notifications WHERE request_id=?", (request_id,))
        db.execute("DELETE FROM project_requests WHERE id=?", (request_id,))
    return {"message":"درخواست حذف شد و ظرفیت شما آزاد شد."}

@app.get("/api/project-requests/{request_id}/profile")
def project_request_profile(request_id: str, user=Depends(current_user)):
    require_approved(user)
    with get_db() as db:
        r=db.execute("SELECT r.*,p.user_id AS employer_id FROM project_requests r JOIN projects p ON p.id=r.project_id WHERE r.id=?",(request_id,)).fetchone()
        if not r: raise HTTPException(404,"درخواست پیدا نشد.")
        if user["id"] not in (r["employer_id"],r["contractor_id"]): raise HTTPException(403,"دسترسی ندارید.")
        other=r["contractor_id"] if user["id"]==r["employer_id"] else r["employer_id"]
        profile=safe_profile(db,other)
    return {"profile":profile}

@app.get("/api/project-requests/{request_id}/messages")
def get_chat_messages(request_id: str, user=Depends(current_user)):
    require_approved(user)
    with get_db() as db:
        ensure_request_party(db,request_id,user["id"])
        rows=db.execute("SELECT id,sender_id,body,created_at FROM project_chat_messages WHERE request_id=? ORDER BY created_at ASC LIMIT 300",(request_id,)).fetchall()
        db.execute("UPDATE project_chat_messages SET is_read=1 WHERE request_id=? AND sender_id<>?",(request_id,user["id"]))
    return {"messages":[dict(x) for x in rows]}

@app.post("/api/project-requests/{request_id}/messages")
def send_chat_message(request_id: str, data: dict, user=Depends(current_user)):
    require_approved(user)
    body=str(data.get("body", "")).strip()
    if not body or len(body)>1500: raise HTTPException(400,"پیام باید بین ۱ تا ۱۵۰۰ کاراکتر باشد.")
    if any(p.search(body) for p in CONTACT_PATTERNS) or re.search(r"(?<!\d)(?:[0-9۰-۹٠-٩][\s().-]*){8,}(?!\d)",body) or contains_spelled_number_sequence(body):
        raise HTTPException(400,"ارسال شماره تماس، ایمیل، لینک، آیدی شبکه‌های اجتماعی یا اطلاعات ارتباطی در گفتگو مجاز نیست. لطفاً پیام را بدون اطلاعات تماس بنویسید.")
    with get_db() as db:
        r=ensure_request_party(db,request_id,user["id"])
        mid=secrets.token_hex(16)
        db.execute("INSERT INTO project_chat_messages(id,request_id,sender_id,body,created_at) VALUES(?,?,?,?,?)",(mid,request_id,user["id"],body,now_iso()))
        other=r["contractor_id"] if user["id"]==r["employer_id"] else r["employer_id"]
        db.execute("INSERT INTO notifications(id,user_id,kind,project_id,request_id,is_read,created_at) VALUES(?,?,?,?,?,?,?)",(secrets.token_hex(16),other,"chat_message",r["project_id"],request_id,0,now_iso()))
    return {"message":"پیام ارسال شد.","id":mid}

# ---------------- uploads ----------------
@app.get("/uploads/{file_path:path}", include_in_schema=False)
def uploaded_file(file_path: str):
    root = UPLOAD_DIR.resolve()
    path = (BASE_DIR / file_path).resolve()

    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(404, "فایل پیدا نشد.")

    if not path.is_file():
        raise HTTPException(404, "فایل پیدا نشد.")

    return FileResponse(path)


# ---------------- site ----------------
_PUBLIC_FILES = {"logo.png", "hero-industrial.png"}


@app.get("/", include_in_schema=False)
def index():
    f = BASE_DIR / "index.html"
    if not f.exists():
        raise HTTPException(404, "index.html کنار app.py پیدا نشد.")
    return FileResponse(f)


@app.get("/projects", include_in_schema=False)
def projects_page():
    f = BASE_DIR / "projects.html"
    if not f.exists():
        raise HTTPException(404, "projects.html کنار app.py پیدا نشد.")
    return FileResponse(f)


@app.get("/my-projects", include_in_schema=False)
def my_projects_page():
    f = BASE_DIR / "workspace.html"
    if not f.exists(): raise HTTPException(404, "workspace.html پیدا نشد.")
    return FileResponse(f)

@app.get("/{name}", include_in_schema=False)
def public_file(name: str):
    if name in _PUBLIC_FILES and (BASE_DIR / name).exists():
        return FileResponse(BASE_DIR / name)
    raise HTTPException(404, "Not found")