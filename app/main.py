import os, re, secrets, uuid
from datetime import datetime
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
app.add_middleware(CORSMiddleware, allow_origins=[], allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(engine)
CATS = [("contractors", "پیمانکاران و مجریان"), ("manufacturers", "تولیدکنندگان"), ("industrial-services", "خدمات صنعتی"),
        ("custom-makers", "سازندگان سفارشی"), ("other", "سایر")]
with SessionLocal() as s:
    if not s.scalar(select(func.count(Category.id))):
        s.add_all([Category(slug=a, name=b) for a, b in CATS]); s.commit()

# ---------- schemas (server-side validation) ----------
class RegisterIn(BaseModel):
    email: EmailStr; password: str = Field(min_length=8, max_length=100)
    role: str = Field(pattern="^(customer|provider)$"); name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=80); kind: str | None = Field(default=None, pattern="^(contractor|manufacturer|service|custom|other)$")
class LoginIn(BaseModel): email: EmailStr; password: str
class ProjectIn(BaseModel):
    title: str = Field(min_length=5, max_length=200); category_id: int; city: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=20, max_length=5000); budget_min: int = Field(ge=0); budget_max: int = Field(ge=0)
    duration_days: int = Field(ge=1, le=3650); requirements: str = Field(default="", max_length=3000)
class ProposalIn(BaseModel): price: int = Field(gt=0); duration_days: int = Field(ge=1, le=3650); description: str = Field(min_length=10, max_length=3000)
class MsgIn(BaseModel): body: str = Field(min_length=1, max_length=2000)
class ContractIn(BaseModel): terms: str = Field(min_length=20, max_length=8000); start_date: str; end_date: str
class ReviewIn(BaseModel): rating: int = Field(ge=1, le=5); body: str = Field(default="", max_length=1500)
class ReasonIn(BaseModel): reason: str = Field(default="", max_length=500)

def ptxt(t: str): return redact(t)[0]
def admin_ids(db): return [u.id for u in db.scalars(select(User).where(User.role == "admin"))]

# ---------- auth ----------
@app.post("/api/auth/register", status_code=201)
def register(d: RegisterIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("reg:" + request.client.host, 5, 3600)
    if db.scalar(select(User).where(User.email == d.email.lower())): raise HTTPException(409, "این ایمیل قبلاً ثبت شده است")
    u = User(email=d.email.lower(), password_hash=hash_pw(d.password), role=d.role, verification="PENDING"); db.add(u); db.flush()
    name, _ = redact(d.name)
    if d.role == "provider": db.add(ProviderProfile(user_id=u.id, name=name, city=d.city, kind=d.kind or "other"))
    else: db.add(CustomerProfile(user_id=u.id, name=name, city=d.city))
    notify(db, None, "ثبت‌نام جدید", f"{d.role} — {name} ({d.city})", admin=True); db.commit()
    return {"token": make_token(u.id), "role": u.role}
@app.post("/api/auth/login")
def login(d: LoginIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("login:" + request.client.host, 10, 60)
    u = db.scalar(select(User).where(User.email == d.email.lower()))
    if not u or not check_pw(d.password, u.password_hash): raise HTTPException(401, "ایمیل یا رمز عبور نادرست است")
    return {"token": make_token(u.id), "role": u.role}
@app.get("/api/me")
def me(u: User = Depends(current_user)): return {"id": u.id, "email": u.email, "role": u.role, "verification": u.verification}

# ---------- public catalog ----------
@app.get("/api/categories")
def categories(db: Session = Depends(get_db)): return [{"id": c.id, "slug": c.slug, "name": c.name} for c in db.scalars(select(Category))]
def pdict(p, db):
    n = db.scalar(select(func.count(Proposal.id)).where(Proposal.project_id == p.id, Proposal.status == "ACTIVE"))
    return {"id": p.id, "title": p.title, "city": p.city, "category_id": p.category_id, "budget_min": p.budget_min, "budget_max": p.budget_max,
            "duration_days": p.duration_days, "status": p.status, "proposal_count": n, "description": p.description, "created_at": p.created_at}
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
    return [{"id": p.user_id, "name": p.name, "kind": p.kind, "city": p.city, "specialty": p.specialty, "rating": p.rating,
             "completed_projects": p.completed_projects, "verified": u.verification == "VERIFIED"} for p, u in db.execute(q.limit(20).offset((max(page, 1) - 1) * 20))]

# ---------- customer: projects ----------
@app.post("/api/projects", status_code=201)
def create_project(d: ProjectIn, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    if d.budget_max < d.budget_min: raise HTTPException(422, "حداکثر بودجه نباید کمتر از حداقل باشد")
    if not db.get(Category, d.category_id): raise HTTPException(422, "دسته نامعتبر است")
    p = Project(customer_id=u.id, category_id=d.category_id, title=ptxt(d.title), description=ptxt(d.description), city=d.city,
                budget_min=d.budget_min, budget_max=d.budget_max, duration_days=d.duration_days, requirements=ptxt(d.requirements), status="DRAFT")
    db.add(p); db.flush(); move(p, "PENDING_REVIEW")
    notify(db, None, "پروژه جدید نیازمند بررسی", f"#{p.id} {p.title} — {p.city}", admin=True,
           buttons=[[{"text": "✅ تأیید پروژه", "callback_data": f"proj:approve:{p.id}"}]])
    audit(db, u.id, "project.create", "project", p.id); db.commit(); return {"id": p.id, "status": p.status}
@app.get("/api/my/projects")
def my_projects(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role == "customer": q = select(Project).where(Project.customer_id == u.id)
    else: q = select(Project).where(Project.selected_provider_id == u.id)
    return [pdict(p, db) for p in db.scalars(q.order_by(Project.id.desc()))]
@app.get("/api/projects/{pid}/proposals")
def project_proposals(pid: int, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p or p.customer_id != u.id: raise HTTPException(404, "پروژه پیدا نشد")
    out = []
    for pr in db.scalars(select(Proposal).where(Proposal.project_id == pid, Proposal.status.in_(["ACTIVE", "SELECTED"]))):
        pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == pr.provider_id))
        out.append({"id": pr.id, "price": pr.price, "duration_days": pr.duration_days, "description": pr.description, "provider": {
            "id": pr.provider_id, "name": pp.name, "city": pp.city, "specialty": pp.specialty, "rating": pp.rating,
            "completed_projects": pp.completed_projects, "experience_years": pp.experience_years}})
    return sorted(out, key=lambda x: x["price"])
@app.post("/api/proposals/{prid}/select")
def select_provider(prid: int, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    pr = db.get(Proposal, prid); p = db.get(Project, pr.project_id) if pr else None
    if not p or p.customer_id != u.id or pr.status != "ACTIVE": raise HTTPException(404, "پیشنهاد پیدا نشد")
    move(p, "PROVIDER_SELECTED"); p.selected_provider_id = pr.provider_id; pr.status = "SELECTED"
    c = Connection(project_id=p.id, proposal_id=pr.id, customer_id=u.id, provider_id=pr.provider_id); db.add(c); db.flush()
    move(p, "CONNECTION_PENDING")
    notify(db, pr.provider_id, "انتخاب شدید", f"کارفرما شما را برای «{p.title}» انتخاب کرد.")
    notify(db, None, "انتخاب ارائه‌دهنده", f"پروژه #{p.id}", admin=True); audit(db, u.id, "provider.select", "project", p.id)
    db.commit(); return {"connection_id": c.id}

# ---------- provider: proposals ----------
@app.get("/api/my/matching-projects")
def matching(u: User = Depends(role("provider")), db: Session = Depends(get_db)):
    pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == u.id))
    q = select(Project).where(Project.status == "RECEIVING_PROPOSALS", Project.city == pp.city)
    return [pdict(p, db) for p in db.scalars(q.order_by(Project.id.desc()).limit(50))]
@app.post("/api/projects/{pid}/proposals", status_code=201)
def send_proposal(pid: int, d: ProposalIn, u: User = Depends(role("provider")), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p or p.status != "RECEIVING_PROPOSALS": raise HTTPException(404, "پروژه در حال دریافت پیشنهاد نیست")
    if db.scalar(select(Proposal).where(Proposal.project_id == pid, Proposal.provider_id == u.id, Proposal.status == "ACTIVE")):
        raise HTTPException(409, "برای این پروژه پیشنهاد فعال دارید")
    pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == u.id))
    if pp.plan == "FREE" and pp.free_used >= config.FREE_PROPOSALS: raise HTTPException(402, "سهم رایگان شما تمام شده؛ اشتراک تهیه کنید")
    pp.free_used += 1
    pr = Proposal(project_id=pid, provider_id=u.id, price=d.price, duration_days=d.duration_days, description=ptxt(d.description)); db.add(pr)
    notify(db, p.customer_id, "پیشنهاد جدید", f"برای «{p.title}» پیشنهاد جدید رسید."); db.commit(); return {"id": pr.id}
@app.post("/api/proposals/{prid}/cancel")
def cancel_proposal(prid: int, u: User = Depends(role("provider")), db: Session = Depends(get_db)):
    pr = db.get(Proposal, prid)
    if not pr or pr.provider_id != u.id or pr.status != "ACTIVE": raise HTTPException(404, "پیشنهاد فعال پیدا نشد")
    pr.status = "CANCELLED"; db.commit(); return {"ok": True}
@app.post("/api/connections/{cid}/accept")
def accept_connection(cid: int, u: User = Depends(role("provider")), db: Session = Depends(get_db)):
    c = db.get(Connection, cid)
    if not c or c.provider_id != u.id or c.status != "PENDING": raise HTTPException(404, "اتصال پیدا نشد")
    p = db.get(Project, c.project_id); c.status = "ACCEPTED"; move(p, "PAYMENT_PENDING")
    notify(db, c.customer_id, "اتصال موفق انجام شد", "اکنون می‌توانید هزینه اتصال را پرداخت کنید.")
    notify(db, None, "قبول اتصال", f"پروژه #{p.id}", admin=True); db.commit(); return {"message": "اتصال موفق انجام شد"}

# ---------- chat (contact info is redacted until payment approved) ----------
def conn_for(cid, u, db):
    c = db.get(Connection, cid)
    if not c or u.id not in (c.customer_id, c.provider_id): raise HTTPException(404, "گفتگو پیدا نشد")
    return c
@app.post("/api/connections/{cid}/messages", status_code=201)
def send_msg(cid: int, d: MsgIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db); rate_limit(f"msg:{u.id}", 30, 60)
    body, flagged = (d.body, False) if c.contact_unlocked else redact(d.body)
    db.add(Message(connection_id=cid, sender_id=u.id, body=body, redacted=flagged)); db.commit()
    return {"body": body, "redacted": flagged}
@app.get("/api/connections/{cid}/messages")
def get_msgs(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    conn_for(cid, u, db)
    return [{"id": m.id, "mine": m.sender_id == u.id, "body": m.body, "at": m.created_at} for m in db.scalars(select(Message).where(Message.connection_id == cid).order_by(Message.id))]
@app.get("/api/connections/{cid}/contact")
def contact(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db)
    if not c.contact_unlocked: raise HTTPException(403, "اطلاعات تماس پس از تأیید پرداخت آزاد می‌شود")
    o = db.get(User, c.provider_id if u.id == c.customer_id else c.customer_id)
    return {"email": o.email, "phone": o.phone, "telegram": o.telegram}

# ---------- invoice / manual payment ----------
def approve_payment(db, inv, actor):
    if inv.status != "AWAITING_PAYMENT": raise HTTPException(409, "این فاکتور قبلاً بررسی شده است")
    c = db.get(Connection, inv.connection_id); p = db.get(Project, inv.project_id)
    inv.status = "PAID"; c.contact_unlocked = True; move(p, "PAYMENT_APPROVED"); move(p, "CONTRACT_PENDING")
    db.add(Payment(invoice_id=inv.id, decided_by=str(actor), result="PAID")); audit(db, actor, "payment.approve", "invoice", inv.id)
    for uid in (c.customer_id, c.provider_id): notify(db, uid, "پرداخت تأیید شد", "اطلاعات تماس آزاد شد. قرارداد را تکمیل کنید.")
def reject_payment(db, inv, actor, reason=""):
    if inv.status != "AWAITING_PAYMENT": raise HTTPException(409, "این فاکتور قبلاً بررسی شده است")
    c = db.get(Connection, inv.connection_id); p = db.get(Project, inv.project_id)
    inv.status = "REJECTED"; inv.reject_reason = reason; move(p, "PAYMENT_REJECTED")
    db.add(Payment(invoice_id=inv.id, decided_by=str(actor), result="REJECTED", reason=reason)); audit(db, actor, "payment.reject", "invoice", inv.id, reason)
    notify(db, c.customer_id, "پرداخت رد شد", reason or "پرداخت تأیید نشد.")
@app.post("/api/connections/{cid}/invoice", status_code=201)
def make_invoice(cid: int, u: User = Depends(role("customer")), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db); p = db.get(Project, c.project_id)
    if c.status != "ACCEPTED" or p.status not in ("PAYMENT_PENDING", "PAYMENT_REJECTED"): raise HTTPException(409, "هنوز امکان پرداخت وجود ندارد")
    old = db.scalar(select(Invoice).where(Invoice.connection_id == cid, Invoice.status == "AWAITING_PAYMENT"))
    if old: return {"invoice": old.number, "n_code": old.n_code, "status": old.status}
    if p.status == "PAYMENT_REJECTED": move(p, "PAYMENT_PENDING")
    inv = Invoice(number=f"INV-{datetime.utcnow():%y%m%d}-{secrets.token_hex(3).upper()}", n_code="N" + secrets.token_hex(4).upper(),
                  connection_id=cid, project_id=p.id, amount=config.CONNECTION_FEE); db.add(inv); db.flush()
    r = notify(db, None, "Invoice جدید", f"فاکتور: {inv.number}\nکد N: {inv.n_code}\nپروژه: {p.id}\nکارفرما: {c.customer_id} | ارائه‌دهنده: {c.provider_id}\nمبلغ: {inv.amount:,}\nوضعیت: در انتظار پرداخت", admin=True,
                buttons=[[{"text": "✅ تأیید پرداخت", "callback_data": f"pay:ok:{inv.id}"}, {"text": "❌ رد پرداخت", "callback_data": f"pay:no:{inv.id}"}]])
    if r and r.get("ok"): inv.tg_message_id = r["result"]["message_id"]
    db.commit()
    return {"invoice": inv.number, "n_code": inv.n_code, "amount": inv.amount, "status": "در انتظار تأیید ادمین",
            "instruction": "برای پرداخت، کد N را به ادمین ارسال کنید و پس از انجام پرداخت منتظر تأیید ادمین باشید."}
@app.get("/api/connections/{cid}/invoice")
def invoice_status(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    conn_for(cid, u, db); inv = db.scalar(select(Invoice).where(Invoice.connection_id == cid).order_by(Invoice.id.desc()))
    if not inv: raise HTTPException(404, "فاکتوری ثبت نشده")
    m = {"AWAITING_PAYMENT": "در انتظار تأیید ادمین", "PAID": "پرداخت تأیید شد", "REJECTED": "پرداخت رد شد"}
    return {"invoice": inv.number, "n_code": inv.n_code, "status": inv.status, "label": m[inv.status]}

# ---------- admin (web) ----------
@app.post("/api/admin/projects/{pid}/approve")
def admin_approve_project(pid: int, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p: raise HTTPException(404, "پروژه پیدا نشد")
    move(p, "PUBLISHED"); move(p, "RECEIVING_PROPOSALS"); audit(db, u.id, "project.approve", "project", pid)
    notify(db, p.customer_id, "پروژه تأیید شد", f"«{p.title}» منتشر شد."); db.commit(); return {"status": p.status}
@app.post("/api/admin/invoices/{iid}/approve")
def admin_pay_ok(iid: int, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "فاکتور پیدا نشد")
    approve_payment(db, inv, f"admin:{u.id}"); db.commit(); return {"status": inv.status}
@app.post("/api/admin/invoices/{iid}/reject")
def admin_pay_no(iid: int, d: ReasonIn, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "فاکتور پیدا نشد")
    reject_payment(db, inv, f"admin:{u.id}", d.reason); db.commit(); return {"status": inv.status}
@app.post("/api/admin/users/{uid}/verify")
def verify_user(uid: int, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "کاربر پیدا نشد")
    t.verification = "VERIFIED"; audit(db, u.id, "user.verify", "user", uid); db.commit(); return {"ok": True}
@app.get("/api/admin/audit")
def audit_list(u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    return [{"actor": a.actor, "action": a.action, "entity": a.entity, "id": a.entity_id, "at": a.created_at} for a in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))]

# ---------- Telegram webhook: bot holds NO logic, Backend decides ----------
@app.post("/api/telegram/webhook/{secret}")
async def tg_webhook(secret: str, request: Request, db: Session = Depends(get_db)):
    if not secrets.compare_digest(secret, config.TG_SECRET): raise HTTPException(404)
    upd = await request.json(); cb = upd.get("callback_query")
    if not cb: return {"ok": True}
    fid = cb["from"]["id"]; msg = cb.get("message", {})
    def answer(t, alert=True): tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": t, "show_alert": alert})
    if fid not in config.ADMIN_TG_IDS:
        audit(db, f"tg:{fid}", "unauthorized.callback", "telegram", 0, cb.get("data", "")); db.commit(); answer("دسترسی مجاز نیست"); return {"ok": True}
    kind, act, sid = cb.get("data", "::").split(":")[:3]; actor = f"tg:{fid}"
    try:
        if kind == "pay":
            inv = db.get(Invoice, int(sid))
            if act == "ok": approve_payment(db, inv, actor); label = "✅ پرداخت تأیید شد"
            else: reject_payment(db, inv, actor, "رد شده توسط ادمین از تلگرام"); label = "❌ پرداخت رد شد"
        elif kind == "proj":
            p = db.get(Project, int(sid)); move(p, "PUBLISHED"); move(p, "RECEIVING_PROPOSALS"); audit(db, actor, "project.approve", "project", p.id); label = "✅ پروژه تأیید شد"
        else: answer("عملیات نامعتبر"); return {"ok": True}
        db.commit()
        tg("editMessageText", {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"], "text": msg.get("text", "") + f"\n\n{label}"})
        answer(label, False)
    except HTTPException as e: db.rollback(); answer(str(e.detail))
    return {"ok": True}

# ---------- contract ----------
@app.put("/api/connections/{cid}/contract")
def save_contract(cid: int, d: ContractIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db)
    if not c.contact_unlocked: raise HTTPException(403, "ابتدا پرداخت باید تأیید شود")
    k = db.scalar(select(Contract).where(Contract.connection_id == cid))
    if k and k.status in ("REVIEW", "APPROVED"): raise HTTPException(409, "قرارداد در حال بررسی یا تأییدشده است")
    pr = db.get(Proposal, c.proposal_id)
    if not k: k = Contract(connection_id=cid, project_id=c.project_id, amount=pr.price); db.add(k)
    k.terms, k.start_date, k.end_date = d.terms, d.start_date, d.end_date; k.customer_accepted = k.provider_accepted = False; k.status = "DRAFT"
    db.commit(); return {"status": k.status}
@app.post("/api/connections/{cid}/contract/accept")
def accept_contract(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db); k = db.scalar(select(Contract).where(Contract.connection_id == cid))
    if not k or k.status != "DRAFT": raise HTTPException(409, "قرارداد آماده تأیید نیست")
    if u.id == c.customer_id: k.customer_accepted = True
    else: k.provider_accepted = True
    if k.customer_accepted and k.provider_accepted:
        k.status = "REVIEW"; move(db.get(Project, c.project_id), "CONTRACT_REVIEW")
        notify(db, None, "قرارداد نیازمند بررسی", f"قرارداد #{k.id}", admin=True,
               buttons=None)
    db.commit(); return {"status": k.status}
@app.post("/api/admin/contracts/{kid}/approve")
def approve_contract(kid: int, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    k = db.get(Contract, kid)
    if not k or k.status != "REVIEW": raise HTTPException(409, "قرارداد در وضعیت بررسی نیست")
    k.status = "APPROVED"; move(db.get(Project, k.project_id), "IN_PROGRESS"); audit(db, u.id, "contract.approve", "contract", kid); db.commit(); return {"ok": True}
@app.post("/api/admin/contracts/{kid}/return")
def return_contract(kid: int, d: ReasonIn, u: User = Depends(role("admin")), db: Session = Depends(get_db)):
    k = db.get(Contract, kid)
    if not k or k.status != "REVIEW": raise HTTPException(409, "قرارداد در وضعیت بررسی نیست")
    k.status = "DRAFT"; k.admin_note = d.reason; k.customer_accepted = k.provider_accepted = False
    move(db.get(Project, k.project_id), "CONTRACT_PENDING"); audit(db, u.id, "contract.return", "contract", kid, d.reason); db.commit(); return {"ok": True}
@app.post("/api/connections/{cid}/cancel")
def cancel_before_contract(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db); p = db.get(Project, c.project_id)
    if p.status in ("IN_PROGRESS", "COMPLETION_PENDING", "COMPLETED"): raise HTTPException(403, "لغو پس از تأیید قرارداد فقط توسط ادمین ممکن است")
    move(p, "RECEIVING_PROPOSALS"); c.status = "CANCELLED"; c.contact_unlocked = False; p.selected_provider_id = None
    db.get(Proposal, c.proposal_id).status = "CANCELLED"; audit(db, u.id, "connection.cancel", "connection", cid); db.commit(); return {"status": p.status}

# ---------- completion + review ----------
@app.post("/api/connections/{cid}/complete")
def complete(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = conn_for(cid, u, db); p = db.get(Project, c.project_id); k = db.scalar(select(Contract).where(Contract.connection_id == cid))
    if p.status not in ("IN_PROGRESS", "COMPLETION_PENDING") or not k: raise HTTPException(409, "پروژه در مرحله اجرا نیست")
    if u.id == c.customer_id: k.customer_done = True
    else: k.provider_done = True
    if p.status == "IN_PROGRESS": move(p, "COMPLETION_PENDING")
    if k.customer_done and k.provider_done:
        move(p, "COMPLETED"); pp = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == c.provider_id)); pp.completed_projects += 1
    db.commit(); return {"status": p.status}
@app.post("/api/projects/{pid}/reviews", status_code=201)
def review(pid: int, d: ReviewIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p or p.status != "COMPLETED" or u.id not in (p.customer_id, p.selected_provider_id): raise HTTPException(403, "امکان ثبت نظر وجود ندارد")
    target = p.selected_provider_id if u.id == p.customer_id else p.customer_id
    if db.scalar(select(Review).where(Review.project_id == pid, Review.author_id == u.id)): raise HTTPException(409, "قبلاً ثبت شده است")
    db.add(Review(project_id=pid, author_id=u.id, target_id=target, rating=d.rating, body=d.body))
    prof = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == target)) or db.scalar(select(CustomerProfile).where(CustomerProfile.user_id == target))
    prof.rating = round((prof.rating * prof.rating_count + d.rating) / (prof.rating_count + 1), 2); prof.rating_count += 1
    db.commit(); return {"ok": True}

# ---------- notifications / upload / reports ----------
@app.get("/api/notifications")
def notifs(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": n.id, "event": n.event, "text": n.text, "at": n.created_at} for n in db.scalars(select(Notification).where(Notification.user_id == u.id).order_by(Notification.id.desc()).limit(50))]
@app.post("/api/upload", status_code=201)
async def upload(f: UploadFile = File(...), u: User = Depends(current_user)):
    ext = os.path.splitext(f.filename or "")[1].lower()
    if ext not in config.ALLOWED_EXT: raise HTTPException(415, "نوع فایل مجاز نیست")
    data = await f.read()
    if len(data) > config.MAX_UPLOAD: raise HTTPException(413, "حجم فایل بیش از حد مجاز است")
    os.makedirs("uploads", exist_ok=True); name = f"{u.id}_{uuid.uuid4().hex}{ext}"
    open(os.path.join("uploads", name), "wb").write(data); return {"file": name}
@app.get("/api/files/{name}")
def get_file(name: str, u: User = Depends(current_user)):
    if not re.fullmatch(r"\d+_[0-9a-f]{32}\.\w+", name): raise HTTPException(404)
    if not name.startswith(f"{u.id}_") and u.role != "admin": raise HTTPException(403, "دسترسی مجاز نیست")
    return FileResponse(os.path.join("uploads", name))
@app.post("/api/report", status_code=201)
def report(target_type: str, target_id: int, d: ReasonIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(Report(reporter_id=u.id, target_type=target_type[:30], target_id=target_id, reason=d.reason)); notify(db, None, "گزارش جدید", f"{target_type} #{target_id}", admin=True); db.commit(); return {"ok": True}
@app.get("/")
def home(): return FileResponse("frontend/index.html")
