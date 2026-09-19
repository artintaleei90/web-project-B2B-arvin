import os, re, secrets, uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from . import config
from .db import Base, engine, get_db, SessionLocal
from .models import *
from .security import hash_pw, check_pw, make_token, current_user, role, rate_limit
from .contact_filter import redact
from .states import move
from .services import audit, notify, notify_admin, tg

app = FastAPI(title="Sanaat Market API")

# ✅ پشتیبانی کامل از CORS برای رفع مشکل Failed to fetch در Live Server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(engine)
CATS = [
    ("contractors", "پیمانکاران و مجریان"),
    ("manufacturers", "تولیدکنندگان"),
    ("industrial-services", "خدمات صنعتی"),
    ("custom-makers", "سازندگان سفارشی"),
    ("other", "سایر")
]

with SessionLocal() as s:
    if not s.scalar(select(func.count(Category.id))):
        s.add_all([Category(slug=a, name=b) for a, b in CATS])
        s.commit()

# ---------- Schemas ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: str = Field(pattern="^(customer|provider)$")
    name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=80)
    kind: str | None = Field(default=None, pattern="^(contractor|manufacturer|service|custom|other)$")

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ProjectIn(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    category_id: int
    city: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=20, max_length=5000)
    budget_min: int = Field(ge=0)
    budget_max: int = Field(ge=0)
    duration_days: int = Field(ge=1, le=3650)
    requirements: str = Field(default="", max_length=3000)

def ptxt(t: str):
    return redact(t)[0]

# ---------- Auth ----------
@app.post("/api/auth/register", status_code=201)
def register(d: RegisterIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("reg:" + (request.client.host if request.client else "127.0.0.1"), 5, 3600)
    if db.scalar(select(User).where(User.email == d.email.lower())):
        raise HTTPException(409, "این ایمیل قبلاً ثبت شده است")
    u = User(email=d.email.lower(), password_hash=hash_pw(d.password), role=d.role, verification="PENDING")
    db.add(u)
    db.flush()
    name, _ = redact(d.name)
    if d.role == "provider":
        db.add(ProviderProfile(user_id=u.id, name=name, city=d.city, kind=d.kind or "other"))
    else:
        db.add(CustomerProfile(user_id=u.id, name=name, city=d.city))
    notify(db, None, "ثبت‌نام جدید", f"{d.role} — {name} ({d.city})", admin=True)
    db.commit()
    return {"token": make_token(u.id), "role": u.role}

@app.post("/api/auth/login")
def login(d: LoginIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("login:" + (request.client.host if request.client else "127.0.0.1"), 10, 60)
    u = db.scalar(select(User).where(User.email == d.email.lower()))
    if not u or not check_pw(d.password, u.password_hash):
        raise HTTPException(401, "ایمیل یا رمز عبور نادرست است")
    return {"token": make_token(u.id), "role": u.role}

@app.get("/api/me")
def me(u: User = Depends(current_user)):
    return {"id": u.id, "email": u.email, "role": u.role, "verification": u.verification}

# ---------- Public Catalog ----------
@app.get("/api/categories")
def categories(db: Session = Depends(get_db)):
    return [{"id": c.id, "slug": c.slug, "name": c.name} for c in db.scalars(select(Category))]

def pdict(p, db):
    n = db.scalar(select(func.count(Proposal.id)).where(Proposal.project_id == p.id, Proposal.status == "ACTIVE"))
    return {
        "id": p.id, "title": p.title, "city": p.city, "category_id": p.category_id,
        "budget_min": p.budget_min, "budget_max": p.budget_max, "duration_days": p.duration_days,
        "status": p.status, "proposal_count": n, "description": p.description, "created_at": p.created_at
    }

@app.get("/api/projects")
def list_projects(city: str | None = None, category_id: int | None = None, page: int = 1, db: Session = Depends(get_db)):
    q = select(Project).where(Project.status == "RECEIVING_PROPOSALS")
    if city and city != "همه شهرها":
        q = q.where(Project.city == city)
    if category_id:
        q = q.where(Project.category_id == category_id)
    return [pdict(p, db) for p in db.scalars(q.order_by(Project.id.desc()).limit(20).offset((max(page, 1) - 1) * 20))]

# ---------- Projects ----------
@app.post("/api/projects", status_code=201)
def create_project(d: ProjectIn, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    if d.budget_max < d.budget_min:
        raise HTTPException(422, "حداکثر بودجه نباید کمتر از حداقل باشد")
    if not db.get(Category, d.category_id):
        raise HTTPException(422, "دسته نامعتبر است")
    p = Project(
        customer_id=u.id, category_id=d.category_id, title=ptxt(d.title),
        description=ptxt(d.description), city=d.city, budget_min=d.budget_min,
        budget_max=d.budget_max, duration_days=d.duration_days, requirements=ptxt(d.requirements), status="DRAFT"
    )
    db.add(p)
    db.flush()
    move(p, "PENDING_REVIEW")
    notify(
        db, None, "پروژه جدید نیازمند بررسی", f"#{p.id} {p.title} — {p.city}", admin=True,
        buttons=[[{"text": "✅ تأیید پروژه", "callback_data": f"proj:approve:{p.id}"}]]
    )
    audit(db, u.id, "project.create", "project", p.id)
    db.commit()
    return {"id": p.id, "status": p.status}

@app.get("/")
def home():
    return FileResponse("frontend/index.html")