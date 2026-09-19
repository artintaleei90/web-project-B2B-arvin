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

# تنظیمات CORS برای ارتباط کامل فرانت‌اند و بک‌اند
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

class ProposalIn(BaseModel):
    price: int = Field(gt=0)
    duration_days: int = Field(ge=1, le=3650)
    description: str = Field(min_length=10, max_length=3000)

class MsgIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class ContractIn(BaseModel):
    terms: str = Field(min_length=20, max_length=8000)
    start_date: str
    end_date: str

class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str = Field(default="", max_length=1500)

class ReasonIn(BaseModel):
    reason: str = Field(default="", max_length=500)

def ptxt(t: str): 
    return redact(t)[0]

# ---------- Auth ----------
@app.post("/api/auth/register", status_code=201)
def register(d: RegisterIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("reg:" + request.client.host, 5, 3600)
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
    
    db.commit()
    notify(db, None, "ثبت‌نام جدید", f"{d.role} — {name} ({d.city})", admin=True)
    return {"token": make_token(u.id), "role": u.role}

@app.post("/api/auth/login")
def login(d: LoginIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("login:" + request.client.host, 10, 60)
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
    if city: q = q.where(Project.city == city)
    if category_id: q = q.where(Project.category_id == category_id)
    return [pdict(p, db) for p in db.scalars(q.order_by(Project.id.desc()).limit(20).offset((max(page, 1) - 1) * 20))]

@app.get("/api/providers")
def providers(city: str | None = None, kind: str | None = None, page: int = 1, db: Session = Depends(get_db)):
    q = select(ProviderProfile, User).join(User, User.id == ProviderProfile.user_id).where(User.is_active == True)
    if city: q = q.where(ProviderProfile.city == city)
    if kind: q = q.where(ProviderProfile.kind == kind)
    return [{
        "id": p.user_id, "name": p.name, "kind": p.kind, "city": p.city,
        "specialty": p.specialty, "rating": p.rating, "completed_projects": p.completed_projects,
        "verified": u.verification == "VERIFIED"
    } for p, u in db.execute(q.limit(20).offset((max(page, 1) - 1) * 20))]

# ---------- Customer: Projects ----------
@app.post("/api/projects", status_code=201)
def create_project(d: ProjectIn, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    if d.budget_max < d.budget_min:
        raise HTTPException(422, "حداکثر بودجه نباید کمتر از حداقل باشد")
    if not db.get(Category, d.category_id):
        raise HTTPException(422, "دسته نامعتبر است")
    
    # ثبت پروژه در حالت DRAFT و انتقال بلافاصله به PENDING_REVIEW
    p = Project(
        customer_id=u.id, category_id=d.category_id, title=ptxt(d.title),
        description=ptxt(d.description), city=d.city, budget_min=d.budget_min,
        budget_max=d.budget_max, duration_days=d.duration_days, requirements=ptxt(d.requirements),
        status="DRAFT"
    )
    db.add(p)
    db.flush()
    move(p, "PENDING_REVIEW")
    audit(db, u.id, "project.create", "project", p.id)
    db.commit()

    # ارسال اعلان به تلگرام ادمین پس از ذخیره قطعی در دیتابیس
    notify(
        db, None, "پروژه جدید نیازمند بررسی", 
        f"عنوان: {p.title}\nشهر: {p.city}\nبودجه: {p.budget_min:,} تا {p.budget_max:,} تومان\nتوضیحات: {p.description}", 
        admin=True,
        buttons=[[{"text": "✅ تأیید پروژه", "callback_data": f"proj:approve:{p.id}"}]]
    )
    
    return {"id": p.id, "status": p.status}

@app.get("/api/my/projects")
def my_projects(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role == "customer":
        q = select(Project).where(Project.customer_id == u.id)
    else:
        q = select(Project).where(Project.selected_provider_id == u.id)
    return [pdict(p, db) for p in db.scalars(q.order_by(Project.id.desc()))]

@app.get("/api/projects/{pid}/proposals")
def project_proposals(pid: int, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p or p.customer_id != u.id:
        raise HTTPException(404, "پروژه پیدا نشد")
    out = []
    for pr in db.scalars(select(Proposal).where(Proposal.project_id == pid, Proposal.status.in_(["ACTIVE", "SELECTED"]))):
        pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == pr.provider_id))
        out.append({
            "id": pr.id, "price": pr.price, "duration_days": pr.duration_days, "description": pr.description,
            "provider": {
                "id": pr.provider_id, "name": pp.name, "city": pp.city, "specialty": pp.specialty,
                "rating": pp.rating, "completed_projects": pp.completed_projects, "experience_years": pp.experience_years
            }
        })
    return sorted(out, key=lambda x: x["price"])

@app.post("/api/proposals/{prid}/select")
def select_provider(prid: int, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    pr = db.get(Proposal, prid)
    p = db.get(Project, pr.project_id) if pr else None
    if not p or p.customer_id != u.id or pr.status != "ACTIVE":
        raise HTTPException(404, "پیشنهاد پیدا نشد")
    move(p, "PROVIDER_SELECTED")
    p.selected_provider_id = pr.provider_id
    pr.status = "SELECTED"
    c = Connection(project_id=p.id, proposal_id=pr.id, customer_id=u.id, provider_id=pr.provider_id)
    db.add(c)
    db.flush()
    move(p, "CONNECTION_PENDING")
    audit(db, u.id, "provider.select", "project", p.id)
    db.commit()
    
    notify(db, pr.provider_id, "انتخاب شدید", f"کارفرما شما را برای «{p.title}» انتخاب کرد.")
    notify(db, None, "انتخاب ارائه‌دهنده", f"پروژه #{p.id}", admin=True)
    return {"connection_id": c.id}

# ---------- Provider: Proposals ----------
@app.get("/api/my/matching-projects")
def matching(u: User = Depends(role("provider")), db: Session = Depends(get_db)):
    pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == u.id))
    q = select(Project).where(Project.status == "RECEIVING_PROPOSALS", Project.city == pp.city)
    return [pdict(p, db) for p in db.scalars(q.order_by(Project.id.desc()).limit(50))]

@app.post("/api/projects/{pid}/proposals", status_code=201)
def send_proposal(pid: int, d: ProposalIn, u: User = Depends(role("provider")), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p or p.status != "RECEIVING_PROPOSALS":
        raise HTTPException(404, "پروژه در حال دریافت پیشنهاد نیست")
    if db.scalar(select(Proposal).where(Proposal.project_id == pid, Proposal.provider_id == u.id, Proposal.status == "ACTIVE")):
        raise HTTPException(409, "برای این پروژه پیشنهاد فعال دارید")
    pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == u.id))
    if pp.plan == "FREE" and pp.free_used >= config.FREE_PROPOSALS:
        raise HTTPException(402, "سهم رایگان شما تمام شده؛ اشتراک تهیه کنید")
    
    pp.free_used += 1
    pr = Proposal(project_id=pid, provider_id=u.id, price=d.price, duration_days=d.duration_days, description=ptxt(d.description))
    db.add(pr)
    db.commit()
    notify(db, p.customer_id, "پیشنهاد جدید", f"برای «{p.title}» پیشنهاد جدید رسید.")
    return {"id": pr.id}

# ---------- Chat ----------
def conn_for(cid, u, db):
    c = db.get(Connection, cid)
    if not c or u.id not in (c.customer_id, c.provider_id):
        raise HTTPException(404, "گفتگو پیدا نشد")
    return c

@app.post("/api/connections/{cid}/messages", status_code=201)
def send_msg(cid: int, d: MsgIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db)
    rate_limit(f"msg:{u.id}", 30, 60)
    body, flagged = (d.body, False) if c.contact_unlocked else redact(d.body)
    db.add(Message(connection_id=cid, sender_id=u.id, body=body, redacted=flagged))
    db.commit()
    return {"body": body, "redacted": flagged}

@app.get("/api/connections/{cid}/messages")
def get_msgs(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    conn_for(cid, u, db)
    return [{"id": m.id, "mine": m.sender_id == u.id, "body": m.body, "at": m.created_at} for m in db.scalars(select(Message).where(Message.connection_id == cid).order_by(Message.id))]

@app.get("/api/connections/{cid}/contact")
def contact(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db)
    if not c.contact_unlocked:
        raise HTTPException(403, "اطلاعات تماس پس از تأیید پرداخت آزاد می‌شود")
    o = db.get(User, c.provider_id if u.id == c.customer_id else c.customer_id)
    return {"email": o.email, "phone": o.phone, "telegram": o.telegram}

# ---------- Invoices & Payments ----------
def approve_payment(db, inv, actor):
    if inv.status != "AWAITING_PAYMENT":
        raise HTTPException(409, "این فاکتور قبلاً بررسی شده است")
    c = db.get(Connection, inv.connection_id)
    p = db.get(Project, inv.project_id)
    inv.status = "PAID"
    c.contact_unlocked = True
    move(p, "PAYMENT_APPROVED")
    move(p, "CONTRACT_PENDING")
    db.add(Payment(invoice_id=inv.id, decided_by=str(actor), result="PAID"))
    audit(db, actor, "payment.approve", "invoice", inv.id)
    for uid in (c.customer_id, c.provider_id):
        notify(db, uid, "پرداخت تأیید شد", "اطلاعات تماس آزاد شد. قرارداد را تکمیل کنید.")

def reject_payment(db, inv, actor, reason=""):
    if inv.status != "AWAITING_PAYMENT":
        raise HTTPException(409, "این فاکتور قبلاً بررسی شده است")
    c = db.get(Connection, inv.connection_id)
    p = db.get(Project, inv.project_id)
    inv.status = "REJECTED"
    inv.reject_reason = reason
    move(p, "PAYMENT_REJECTED")
    db.add(Payment(invoice_id=inv.id, decided_by=str(actor), result="REJECTED", reason=reason))
    audit(db, actor, "payment.reject", "invoice", inv.id, reason)
    notify(db, c.customer_id, "پرداخت رد شد", reason or "پرداخت تأیید نشد.")

# ---------- Admin Web API ----------
@app.post("/api/admin/projects/{pid}/approve")
def admin_approve_project(pid: int, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "پروژه پیدا نشد")
    move(p, "PUBLISHED")
    move(p, "RECEIVING_PROPOSALS")
    audit(db, u.id, "project.approve", "project", pid)
    db.commit()
    notify(db, p.customer_id, "پروژه تأیید شد", f"«{p.title}» منتشر شد.")
    return {"status": p.status}

# ---------- Telegram Webhook (اصلی‌ترین بخش اعتبارسنجی و اکشن‌ها) ----------
@app.post("/api/telegram/webhook/{secret}")
async def tg_webhook(secret: str, request: Request, db: Session = Depends(get_db)):
    if not secrets.compare_digest(secret, config.TG_SECRET):
        raise HTTPException(404)
    
    upd = await request.json()
    cb = upd.get("callback_query")
    if not cb:
        return {"ok": True}
    
    fid = cb["from"]["id"]
    msg = cb.get("message", {})
    
    def answer(t, alert=True):
        tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": t, "show_alert": alert})
    
    if fid not in config.ADMIN_TG_IDS:
        audit(db, f"tg:{fid}", "unauthorized.callback", "telegram", 0, cb.get("data", ""))
        db.commit()
        answer("دسترسی مجاز نیست")
        return {"ok": True}
    
    kind, act, sid = cb.get("data", "::").split(":")[:3]
    actor = f"tg:{fid}"
    
    try:
        if kind == "pay":
            inv = db.get(Invoice, int(sid))
            if act == "ok":
                approve_payment(db, inv, actor)
                label = "✅ پرداخت تأیید شد"
            else:
                reject_payment(db, inv, actor, "رد شده توسط ادمین از تلگرام")
                label = "❌ پرداخت رد شد"
        elif kind == "proj":
            p = db.get(Project, int(sid))
            move(p, "PUBLISHED")
            move(p, "RECEIVING_PROPOSALS")
            audit(db, actor, "project.approve", "project", p.id)
            label = "✅ پروژه با موفقیت تأیید شد"
        else:
            answer("عملیات نامعتبر")
            return {"ok": True}
        
        db.commit()
        tg("editMessageText", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg["message_id"],
            "text": msg.get("text", "") + f"\n\nنتیجه: {label}"
        })
        answer(label, False)
    except HTTPException as e:
        db.rollback()
        answer(str(e.detail))
    return {"ok": True}

# ---------- Root & Healthcheck ----------
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return FileResponse("frontend/index.html")

@app.get("/health")
def health_check():
    return {"status": "ok"}