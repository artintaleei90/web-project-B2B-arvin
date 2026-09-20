import secrets
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from . import config
from .db import Base, engine, get_db, SessionLocal
from .models import *
from .security import hash_pw, check_pw, make_token, current_user, optional_user, role, rate_limit
from .contact_filter import redact
from .states import move
from .services import audit, notify, tg

app = FastAPI(title="Sanaat Market API", version="1.0.0")
if config.FRONTEND_ORIGINS == ["*"]:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
else:
    app.add_middleware(CORSMiddleware, allow_origins=config.FRONTEND_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

Base.metadata.create_all(engine)
CATS = [("contractors", "پیمانکاران و مجریان"), ("manufacturers", "تولیدکنندگان"), ("industrial-services", "خدمات صنعتی"), ("custom-makers", "سازندگان سفارشی"), ("other", "سایر")]
SERVICES = [
    ("industrial-electricity", "برق صنعتی", "طراحی، اجرا و تعمیرات برق صنعتی"),
    ("industrial-automation", "اتوماسیون صنعتی", "PLC، کنترل، ابزار دقیق و اتوماسیون"),
    ("shed-construction", "ساخت سوله", "طراحی و اجرای سازه و سوله صنعتی"),
    ("panel-building", "ساخت تابلو برق", "ساخت و مونتاژ تابلوهای برق صنعتی"),
    ("machinery", "ماشین‌آلات صنعتی", "طراحی و تولید ماشین‌آلات و خطوط تولید"),
    ("maintenance", "تعمیرات و نگهداری", "سرویس، تعمیر و نگهداری تجهیزات صنعتی"),
]
with SessionLocal() as s:
    if not s.scalar(select(func.count(Category.id))):
        s.add_all([Category(slug=a, name=b) for a, b in CATS]); s.commit()
    if not s.scalar(select(func.count(Service.id))):
        cats = {c.slug: c.id for c in s.scalars(select(Category))}
        s.add_all([Service(slug=slug, title=title, category_id=cats["industrial-services"], description=desc) for slug, title, desc in SERVICES]); s.commit()

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: str = Field(pattern="^(customer|provider)$")
    name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=80)
    kind: str | None = Field(default=None, pattern="^(contractor|manufacturer|service|custom|other)$")

class LoginIn(BaseModel): email: EmailStr; password: str
class ProjectIn(BaseModel):
    title: str = Field(min_length=5, max_length=200); category_id: int; city: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=20, max_length=5000); budget_min: int = Field(ge=0); budget_max: int = Field(ge=0)
    duration_days: int = Field(ge=1, le=3650); requirements: str = Field(default="", max_length=3000)
class ProposalIn(BaseModel):
    price: int = Field(gt=0); duration_days: int = Field(ge=1, le=3650); description: str = Field(min_length=10, max_length=3000)
class MsgIn(BaseModel): body: str = Field(min_length=1, max_length=2000)
class ContractIn(BaseModel): terms: str = Field(min_length=20, max_length=8000); start_date: str; end_date: str
class ReviewIn(BaseModel): rating: int = Field(ge=1, le=5); body: str = Field(default="", max_length=1500)
class ReasonIn(BaseModel): reason: str = Field(default="", max_length=500)
class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=160); city: str = Field(min_length=2, max_length=80)
    specialty: str = Field(default="", max_length=160); bio: str = Field(default="", max_length=3000); experience_years: int = Field(default=0, ge=0, le=100)

def clean(t: str): return redact(t)[0]
def p_dict(p, db):
    n = db.scalar(select(func.count(Proposal.id)).where(Proposal.project_id == p.id, Proposal.status == "ACTIVE")) or 0
    return {"id":p.id,"title":p.title,"city":p.city,"category_id":p.category_id,"budget_min":p.budget_min,"budget_max":p.budget_max,"duration_days":p.duration_days,"status":p.status,"proposal_count":n,"description":p.description,"requirements":p.requirements,"created_at":p.created_at.isoformat() if p.created_at else None}
def profile_dict(pp, u):
    return {"id":u.id,"name":pp.name,"kind":pp.kind,"city":pp.city,"specialty":pp.specialty,"bio":pp.bio,"rating":pp.rating,"rating_count":pp.rating_count,"completed_projects":pp.completed_projects,"experience_years":pp.experience_years,"verified":u.verification=="VERIFIED","plan":pp.plan}
def conn_for(cid,u,db):
    c=db.get(Connection,cid)
    if not c or u.id not in (c.customer_id,c.provider_id): raise HTTPException(404,"گفتگو پیدا نشد")
    return c

def create_invoice(db,c):
    existing=db.scalar(select(Invoice).where(Invoice.connection_id==c.id,Invoice.status.in_(["AWAITING_PAYMENT","PAID"])))
    if existing: return existing
    number=f"SM-{datetime.utcnow():%Y%m%d}-{c.id:06d}-{secrets.token_hex(2).upper()}"; ncode=f"N-{secrets.token_hex(4).upper()}"
    inv=Invoice(number=number,n_code=ncode,connection_id=c.id,project_id=c.project_id,amount=config.CONNECTION_FEE)
    db.add(inv); db.flush(); return inv

def approve_payment(db,inv,actor):
    if not inv or inv.status!="AWAITING_PAYMENT": raise HTTPException(409,"این فاکتور قبلاً بررسی شده است")
    c=db.get(Connection,inv.connection_id); p=db.get(Project,inv.project_id)
    inv.status="PAID"; c.status="ACCEPTED"; c.contact_unlocked=True; move(p,"PAYMENT_APPROVED"); move(p,"CONTRACT_PENDING")
    db.add(Payment(invoice_id=inv.id,decided_by=str(actor),result="PAID")); audit(db,actor,"payment.approve","invoice",inv.id)
    for uid in (c.customer_id,c.provider_id): notify(db,uid,"پرداخت تأیید شد","اطلاعات تماس آزاد شد. قرارداد را تکمیل کنید.")

def reject_payment(db,inv,actor,reason=""):
    if not inv or inv.status!="AWAITING_PAYMENT": raise HTTPException(409,"این فاکتور قبلاً بررسی شده است")
    c=db.get(Connection,inv.connection_id); p=db.get(Project,inv.project_id); inv.status="REJECTED"; inv.reject_reason=reason; move(p,"PAYMENT_REJECTED")
    db.add(Payment(invoice_id=inv.id,decided_by=str(actor),result="REJECTED",reason=reason)); audit(db,actor,"payment.reject","invoice",inv.id,reason); notify(db,c.customer_id,"پرداخت رد شد",reason or "پرداخت تأیید نشد.")

@app.post("/api/auth/register",status_code=201)
def register(d:RegisterIn,request:Request,db:Session=Depends(get_db)):
    rate_limit("reg:"+request.client.host,5,3600)
    email=d.email.lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"این ایمیل قبلاً ثبت شده است")
    u=User(email=email,password_hash=hash_pw(d.password),role=d.role,verification="PENDING"); db.add(u); db.flush(); name=clean(d.name)
    if d.role=="provider": db.add(ProviderProfile(user_id=u.id,name=name,city=d.city,kind=d.kind or "other"))
    else: db.add(CustomerProfile(user_id=u.id,name=name,city=d.city))
    audit(db,u.id,"user.register","user",u.id); notify(db,None,"ثبت‌نام جدید",f"{d.role} — {name} ({d.city})",admin=True); db.commit()
    return {"token":make_token(u.id),"role":u.role}

@app.post("/api/auth/login")
def login(d:LoginIn,request:Request,db:Session=Depends(get_db)):
    rate_limit("login:"+request.client.host,10,60); u=db.scalar(select(User).where(User.email==d.email.lower()))
    if not u or not check_pw(d.password,u.password_hash): raise HTTPException(401,"ایمیل یا رمز عبور نادرست است")
    audit(db,u.id,"user.login","user",u.id); db.commit(); return {"token":make_token(u.id),"role":u.role}

@app.get("/api/me")
def me(u:User=Depends(current_user),db:Session=Depends(get_db)):
    out={"id":u.id,"email":u.email,"role":u.role,"verification":u.verification}
    if u.role=="provider": out["profile"]=profile_dict(db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==u.id)),u)
    elif u.role=="customer":
        pp=db.scalar(select(CustomerProfile).where(CustomerProfile.user_id==u.id)); out["profile"]={"id":u.id,"name":pp.name,"city":pp.city,"field":pp.field,"rating":pp.rating}
    return out

@app.get("/api/categories")
def categories(db:Session=Depends(get_db)): return [{"id":c.id,"slug":c.slug,"name":c.name} for c in db.scalars(select(Category).order_by(Category.id))]
@app.get("/api/services")
def services(db:Session=Depends(get_db)):
    return [{"id":s.id,"slug":s.slug,"title":s.title,"category_id":s.category_id,"description":s.description} for s in db.scalars(select(Service).order_by(Service.id))]

@app.get("/api/projects")
def list_projects(city:str|None=None,category_id:int|None=None,q:str|None=None,page:int=1,db:Session=Depends(get_db)):
    query=select(Project).where(Project.status=="RECEIVING_PROPOSALS")
    if city: query=query.where(Project.city.ilike(f"%{city}%"))
    if category_id: query=query.where(Project.category_id==category_id)
    if q: query=query.where(or_(Project.title.ilike(f"%{q}%"),Project.description.ilike(f"%{q}%")))
    return [p_dict(p,db) for p in db.scalars(query.order_by(Project.id.desc()).limit(20).offset((max(page,1)-1)*20))]

@app.get("/api/projects/{pid}")
def project_detail(pid:int,u:User|None=Depends(optional_user),db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p: raise HTTPException(404,"پروژه پیدا نشد")
    public_status={"RECEIVING_PROPOSALS","PROVIDER_SELECTED","CONNECTION_PENDING","PAYMENT_PENDING","PAYMENT_APPROVED","CONTRACT_PENDING","CONTRACT_REVIEW","IN_PROGRESS","COMPLETION_PENDING","COMPLETED"}
    if p.status not in public_status and not (u and (u.id==p.customer_id or u.id==p.selected_provider_id or u.role=="admin")):
        raise HTTPException(404,"پروژه پیدا نشد")
    return p_dict(p,db)

@app.get("/api/providers")
def providers(city:str|None=None,kind:str|None=None,q:str|None=None,page:int=1,db:Session=Depends(get_db)):
    query=select(ProviderProfile,User).join(User,User.id==ProviderProfile.user_id).where(User.is_active.is_(True))
    if city: query=query.where(ProviderProfile.city.ilike(f"%{city}%"))
    if kind: query=query.where(ProviderProfile.kind==kind)
    if q: query=query.where(or_(ProviderProfile.name.ilike(f"%{q}%"),ProviderProfile.specialty.ilike(f"%{q}%")))
    return [profile_dict(p,u) for p,u in db.execute(query.order_by(ProviderProfile.rating.desc(),ProviderProfile.id.desc()).limit(20).offset((max(page,1)-1)*20))]

@app.get("/api/providers/{uid}")
def provider_detail(uid:int,db:Session=Depends(get_db)):
    u=db.get(User,uid); pp=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==uid))
    if not u or not pp or u.role!="provider": raise HTTPException(404,"ارائه‌دهنده پیدا نشد")
    return profile_dict(pp,u)

@app.put("/api/me/profile")
def update_profile(d:ProfileIn,u:User=Depends(current_user),db:Session=Depends(get_db)):
    if u.role=="provider":
        pp=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==u.id)); pp.name=clean(d.name); pp.city=d.city; pp.specialty=clean(d.specialty); pp.bio=clean(d.bio); pp.experience_years=d.experience_years
    else:
        pp=db.scalar(select(CustomerProfile).where(CustomerProfile.user_id==u.id)); pp.name=clean(d.name); pp.city=d.city
    db.commit(); return {"ok":True}

@app.post("/api/projects",status_code=201)
def create_project(d:ProjectIn,u:User=Depends(role("customer")),db:Session=Depends(get_db)):
    if d.budget_max<d.budget_min: raise HTTPException(422,"حداکثر بودجه نباید کمتر از حداقل باشد")
    if not db.get(Category,d.category_id): raise HTTPException(422,"دسته نامعتبر است")
    p=Project(customer_id=u.id,category_id=d.category_id,title=clean(d.title),description=clean(d.description),city=d.city,budget_min=d.budget_min,budget_max=d.budget_max,duration_days=d.duration_days,requirements=clean(d.requirements),status="DRAFT")
    db.add(p); db.flush(); move(p,"PENDING_REVIEW"); audit(db,u.id,"project.create","project",p.id); db.commit()
    notify(db,None,"پروژه جدید نیازمند بررسی",f"#{p.id} {p.title} — {p.city}",admin=True,buttons=[[{"text":"✅ تأیید پروژه","callback_data":f"proj:approve:{p.id}"},{"text":"❌ رد پروژه","callback_data":f"proj:reject:{p.id}"}]])
    return {"id":p.id,"status":p.status}

@app.get("/api/my/projects")
def my_projects(u:User=Depends(current_user),db:Session=Depends(get_db)):
    q=select(Project).where(Project.customer_id==u.id) if u.role=="customer" else select(Project).where(Project.selected_provider_id==u.id)
    return [p_dict(p,db) for p in db.scalars(q.order_by(Project.id.desc()))]

@app.get("/api/projects/{pid}/proposals")
def project_proposals(pid:int,u:User=Depends(role("customer")),db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p or p.customer_id!=u.id: raise HTTPException(404,"پروژه پیدا نشد")
    out=[]
    for pr in db.scalars(select(Proposal).where(Proposal.project_id==pid,Proposal.status.in_(["ACTIVE","SELECTED"]))):
        pp=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==pr.provider_id)); pu=db.get(User,pr.provider_id)
        out.append({"id":pr.id,"price":pr.price,"duration_days":pr.duration_days,"description":pr.description,"status":pr.status,"provider":profile_dict(pp,pu)})
    return sorted(out,key=lambda x:x["price"])

@app.post("/api/proposals/{prid}/select")
def select_provider(prid:int,u:User=Depends(role("customer")),db:Session=Depends(get_db)):
    pr=db.get(Proposal,prid); p=db.get(Project,pr.project_id) if pr else None
    if not p or p.customer_id!=u.id or pr.status!="ACTIVE": raise HTTPException(404,"پیشنهاد پیدا نشد")
    if db.scalar(select(Connection).where(Connection.project_id==p.id,Connection.status.in_(["PENDING","ACCEPTED"]))): raise HTTPException(409,"برای این پروژه اتصال فعالی وجود دارد")
    move(p,"PROVIDER_SELECTED"); p.selected_provider_id=pr.provider_id; pr.status="SELECTED"; c=Connection(project_id=p.id,proposal_id=pr.id,customer_id=u.id,provider_id=pr.provider_id); db.add(c); db.flush(); move(p,"CONNECTION_PENDING"); audit(db,u.id,"provider.select","project",p.id); db.commit(); notify(db,pr.provider_id,"انتخاب شدید",f"کارفرما شما را برای «{p.title}» انتخاب کرد."); return {"connection_id":c.id}

@app.get("/api/my/matching-projects")
def matching(u:User=Depends(role("provider")),db:Session=Depends(get_db)):
    pp=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==u.id))
    q=select(Project).where(Project.status=="RECEIVING_PROPOSALS",Project.city==pp.city)
    return [p_dict(p,db) for p in db.scalars(q.order_by(Project.id.desc()).limit(50))]

@app.post("/api/projects/{pid}/proposals",status_code=201)
def send_proposal(pid:int,d:ProposalIn,u:User=Depends(role("provider")),db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p or p.status!="RECEIVING_PROPOSALS": raise HTTPException(404,"پروژه در حال دریافت پیشنهاد نیست")
    if p.city != db.scalar(select(ProviderProfile.city).where(ProviderProfile.user_id==u.id)): raise HTTPException(403,"این پروژه خارج از شهر فعال شماست")
    if db.scalar(select(Proposal).where(Proposal.project_id==pid,Proposal.provider_id==u.id,Proposal.status=="ACTIVE")): raise HTTPException(409,"برای این پروژه پیشنهاد فعال دارید")
    pp=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==u.id))
    if pp.plan=="FREE" and pp.free_used>=config.FREE_PROPOSALS: raise HTTPException(402,"سهم رایگان شما تمام شده؛ اشتراک تهیه کنید")
    pp.free_used+=1; pr=Proposal(project_id=pid,provider_id=u.id,price=d.price,duration_days=d.duration_days,description=clean(d.description)); db.add(pr); db.commit(); notify(db,p.customer_id,"پیشنهاد جدید",f"برای «{p.title}» پیشنهاد جدید رسید."); db.commit(); return {"id":pr.id}

@app.post("/api/connections/{cid}/accept")
def accept_connection(cid:int,u:User=Depends(role("provider")),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db)
    if c.provider_id!=u.id or c.status!="PENDING": raise HTTPException(409,"این اتصال قابل پذیرش نیست")
    c.status="ACCEPTED"; p=db.get(Project,c.project_id); move(p,"PAYMENT_PENDING"); audit(db,u.id,"connection.accept","connection",cid); db.commit(); notify(db,c.customer_id,"اتصال پذیرفته شد","اکنون می‌توانید هزینه اتصال را پرداخت کنید."); return {"status":c.status}

@app.get("/api/my/connections")
def my_connections(u:User=Depends(current_user),db:Session=Depends(get_db)):
    q=select(Connection).where(or_(Connection.customer_id==u.id,Connection.provider_id==u.id)).order_by(Connection.id.desc())
    out=[]
    for c in db.scalars(q):
        p=db.get(Project,c.project_id); inv=db.scalar(select(Invoice).where(Invoice.connection_id==c.id).order_by(Invoice.id.desc())); out.append({"id":c.id,"project":p_dict(p,db),"status":c.status,"contact_unlocked":c.contact_unlocked,"invoice":None if not inv else {"id":inv.id,"number":inv.number,"n_code":inv.n_code,"amount":inv.amount,"status":inv.status}})
    return out

@app.post("/api/connections/{cid}/messages",status_code=201)
def send_msg(cid:int,d:MsgIn,u:User=Depends(current_user),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db); rate_limit(f"msg:{u.id}",30,60); body,flagged=(d.body,False) if c.contact_unlocked else redact(d.body); db.add(Message(connection_id=cid,sender_id=u.id,body=body,redacted=flagged)); db.commit(); return {"body":body,"redacted":flagged}

@app.get("/api/connections/{cid}/messages")
def get_msgs(cid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
    conn_for(cid,u,db); return [{"id":m.id,"mine":m.sender_id==u.id,"body":m.body,"at":m.created_at.isoformat()} for m in db.scalars(select(Message).where(Message.connection_id==cid).order_by(Message.id))]

@app.get("/api/connections/{cid}/contact")
def contact(cid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db)
    if not c.contact_unlocked: raise HTTPException(403,"اطلاعات تماس پس از تأیید پرداخت آزاد می‌شود")
    o=db.get(User,c.provider_id if u.id==c.customer_id else c.customer_id); return {"email":o.email,"phone":o.phone,"telegram":o.telegram}

@app.post("/api/connections/{cid}/invoice")
def invoice(cid:int,u:User=Depends(role("customer")),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db)
    if c.customer_id!=u.id or c.status!="ACCEPTED": raise HTTPException(409,"اتصال هنوز توسط ارائه‌دهنده پذیرفته نشده است")
    inv=create_invoice(db,c); p=db.get(Project,c.project_id)
    move(p,"PAYMENT_PENDING") if p.status=="CONNECTION_PENDING" else None
    audit(db,u.id,"invoice.create","invoice",inv.id); db.commit()
    notify(db,None,"Invoice جدید",f"فاکتور {inv.number}\nکد N: {inv.n_code}\nمبلغ: {inv.amount:,} تومان\nپروژه: #{p.id}",admin=True,buttons=[[{"text":"✅ تأیید پرداخت","callback_data":f"pay:ok:{inv.id}"},{"text":"❌ رد پرداخت","callback_data":f"pay:no:{inv.id}"}]])
    return {"id":inv.id,"number":inv.number,"n_code":inv.n_code,"amount":inv.amount,"status":inv.status}

@app.get("/api/admin/summary")
def admin_summary(u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    return {"users":db.scalar(select(func.count(User.id))) or 0,"providers":db.scalar(select(func.count(User.id)).where(User.role=="provider")) or 0,"customers":db.scalar(select(func.count(User.id)).where(User.role=="customer")) or 0,"pending_projects":db.scalar(select(func.count(Project.id)).where(Project.status=="PENDING_REVIEW")) or 0,"pending_payments":db.scalar(select(func.count(Invoice.id)).where(Invoice.status=="AWAITING_PAYMENT")) or 0,"contracts":db.scalar(select(func.count(Contract.id))) or 0}

@app.get("/api/admin/projects")
def admin_projects(u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    return [p_dict(p,db) for p in db.scalars(select(Project).order_by(Project.id.desc()).limit(100))]

@app.post("/api/admin/projects/{pid}/approve")
def admin_approve_project(pid:int,u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p: raise HTTPException(404,"پروژه پیدا نشد")
    move(p,"PUBLISHED"); move(p,"RECEIVING_PROPOSALS"); audit(db,u.id,"project.approve","project",pid); db.commit(); notify(db,p.customer_id,"پروژه تأیید شد",f"«{p.title}» منتشر شد."); return {"status":p.status}

@app.post("/api/admin/projects/{pid}/reject")
def admin_reject_project(pid:int,d:ReasonIn=ReasonIn(),u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p: raise HTTPException(404,"پروژه پیدا نشد")
    move(p,"CANCELLED"); audit(db,u.id,"project.reject","project",pid,d.reason); db.commit(); notify(db,p.customer_id,"پروژه رد شد",d.reason or "پروژه توسط ادمین رد شد."); return {"status":p.status}

@app.get("/api/admin/invoices")
def admin_invoices(u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    return [{"id":i.id,"number":i.number,"n_code":i.n_code,"project_id":i.project_id,"amount":i.amount,"status":i.status,"created_at":i.created_at.isoformat()} for i in db.scalars(select(Invoice).order_by(Invoice.id.desc()).limit(100))]

@app.post("/api/admin/invoices/{iid}/approve")
def admin_approve_invoice(iid:int,u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    inv=db.get(Invoice,iid); approve_payment(db,inv,u.id); db.commit(); return {"status":inv.status}

@app.post("/api/admin/invoices/{iid}/reject")
def admin_reject_invoice(iid:int,d:ReasonIn=ReasonIn(),u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    inv=db.get(Invoice,iid); reject_payment(db,inv,u.id,d.reason); db.commit(); return {"status":inv.status}

@app.put("/api/connections/{cid}/contract")
def upsert_contract(cid:int,d:ContractIn,u:User=Depends(current_user),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db)
    if not c.contact_unlocked: raise HTTPException(403,"ابتدا پرداخت باید تأیید شود")
    contract=db.scalar(select(Contract).where(Contract.connection_id==cid)); p=db.get(Project,c.project_id); inv=db.scalar(select(Invoice).where(Invoice.connection_id==cid,Invoice.status=="PAID"))
    if not contract: contract=Contract(connection_id=cid,project_id=p.id,amount=inv.amount if inv else 0); db.add(contract)
    contract.terms=clean(d.terms); contract.start_date=d.start_date; contract.end_date=d.end_date; contract.status="REVIEW"; audit(db,u.id,"contract.update","contract",contract.id or 0); db.commit();
    if p.status=="CONTRACT_PENDING": move(p,"CONTRACT_REVIEW"); db.commit()
    return {"id":contract.id,"status":contract.status}

@app.post("/api/connections/{cid}/contract/accept")
def accept_contract(cid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db); contract=db.scalar(select(Contract).where(Contract.connection_id==cid))
    if not contract: raise HTTPException(404,"قرارداد پیدا نشد")
    if u.id==c.customer_id: contract.customer_accepted=True
    elif u.id==c.provider_id: contract.provider_accepted=True
    else: raise HTTPException(403,"دسترسی مجاز نیست")
    if contract.customer_accepted and contract.provider_accepted: contract.status="REVIEW"
    db.commit(); return {"status":contract.status,"customer_accepted":contract.customer_accepted,"provider_accepted":contract.provider_accepted}

@app.get("/api/connections/{cid}/contract")
def get_contract(cid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
    conn_for(cid,u,db); c=db.scalar(select(Contract).where(Contract.connection_id==cid))
    if not c: raise HTTPException(404,"قرارداد پیدا نشد")
    return {"id":c.id,"terms":c.terms,"amount":c.amount,"start_date":c.start_date,"end_date":c.end_date,"customer_accepted":c.customer_accepted,"provider_accepted":c.provider_accepted,"status":c.status,"admin_note":c.admin_note}

@app.get("/api/admin/contracts")
def admin_contracts(u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    return [{"id":c.id,"project_id":c.project_id,"connection_id":c.connection_id,"status":c.status,"amount":c.amount,"customer_accepted":c.customer_accepted,"provider_accepted":c.provider_accepted} for c in db.scalars(select(Contract).order_by(Contract.id.desc()))]

@app.post("/api/admin/contracts/{cid}/approve")
def admin_contract_approve(cid:int,u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    c=db.get(Contract,cid)
    if not c: raise HTTPException(404,"قرارداد پیدا نشد")
    if not (c.customer_accepted and c.provider_accepted): raise HTTPException(409,"هر دو طرف باید قرارداد را بپذیرند")
    c.status="APPROVED"; p=db.get(Project,c.project_id); move(p,"IN_PROGRESS"); audit(db,u.id,"contract.approve","contract",cid); db.commit(); return {"status":c.status}

@app.post("/api/connections/{cid}/complete")
def complete(cid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db); contract=db.scalar(select(Contract).where(Contract.connection_id==cid)); p=db.get(Project,c.project_id)
    if not contract or contract.status!="APPROVED" or p.status!="IN_PROGRESS": raise HTTPException(409,"پروژه هنوز قابل تکمیل نیست")
    if u.id==c.customer_id: contract.customer_done=True
    elif u.id==c.provider_id: contract.provider_done=True
    if contract.customer_done and contract.provider_done:
        move(p,"COMPLETION_PENDING"); move(p,"COMPLETED")
        for uid in (c.customer_id,c.provider_id):
            pp=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==uid))
            if pp: pp.completed_projects+=1
    db.commit(); return {"status":p.status,"customer_done":contract.customer_done,"provider_done":contract.provider_done}

@app.post("/api/projects/{pid}/reviews")
def review(pid:int,d:ReviewIn,u:User=Depends(current_user),db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p or p.status!="COMPLETED": raise HTTPException(409,"پروژه هنوز تکمیل نشده است")
    if u.id!=p.customer_id and u.id!=p.selected_provider_id: raise HTTPException(403,"شما در این پروژه عضو نیستید")
    target=p.selected_provider_id if u.id==p.customer_id else p.customer_id
    if db.scalar(select(Review).where(Review.project_id==pid,Review.author_id==u.id)): raise HTTPException(409,"قبلاً امتیاز ثبت کرده‌اید")
    r=Review(project_id=pid,author_id=u.id,target_id=target,rating=d.rating,body=clean(d.body)); db.add(r)
    target_user=db.get(User,target)
    if target_user.role=="provider": prof=db.scalar(select(ProviderProfile).where(ProviderProfile.user_id==target)); prof.rating_count+=1; prof.rating=((prof.rating*(prof.rating_count-1))+d.rating)/prof.rating_count
    else: prof=db.scalar(select(CustomerProfile).where(CustomerProfile.user_id==target)); prof.rating_count+=1; prof.rating=((prof.rating*(prof.rating_count-1))+d.rating)/prof.rating_count
    db.commit(); return {"id":r.id}

@app.post("/api/connections/{cid}/cancel")
def cancel(cid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
    c=conn_for(cid,u,db); p=db.get(Project,c.project_id)
    if p.status not in {"CONNECTION_PENDING","PAYMENT_PENDING","PAYMENT_REJECTED","CONTRACT_PENDING","CONTRACT_REVIEW"}: raise HTTPException(403,"در این مرحله لغو عادی امکان‌پذیر نیست")
    c.status="CANCELLED"; p.selected_provider_id=None; pr=db.get(Proposal,c.proposal_id); pr.status="CANCELLED" if pr else None; move(p,"RECEIVING_PROPOSALS"); db.commit(); return {"status":p.status}

@app.post("/api/upload")
async def upload(file:UploadFile=File(...),u:User=Depends(current_user)):
    ext=Path(file.filename or "").suffix.lower()
    if ext not in config.ALLOWED_EXT: raise HTTPException(400,"نوع فایل مجاز نیست")
    data=await file.read(config.MAX_UPLOAD+1)
    if len(data)>config.MAX_UPLOAD: raise HTTPException(413,"حجم فایل بیش از حد مجاز است")
    safe=f"{u.id}_{secrets.token_hex(12)}{ext}"; path=config.UPLOAD_DIR/safe; path.write_bytes(data)
    return {"filename":safe,"size":len(data)}

@app.get("/api/admin/users")
def admin_users(u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    users=[]
    for x in db.scalars(select(User).order_by(User.id.desc()).limit(200)):
        users.append({"id":x.id,"email":x.email,"role":x.role,"verification":x.verification,"is_active":x.is_active,"created_at":x.created_at.isoformat() if x.created_at else None})
    return users

@app.post("/api/admin/users/{uid}/verify")
def admin_verify_user(uid:int,u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    target=db.get(User,uid)
    if not target: raise HTTPException(404,"کاربر پیدا نشد")
    target.verification="VERIFIED"; audit(db,u.id,"user.verify","user",uid); db.commit(); notify(db,uid,"حساب تأیید شد","حساب شما توسط صنعت مارکت تأیید شد."); db.commit(); return {"verification":target.verification}

@app.post("/api/admin/users/{uid}/reject")
def admin_reject_user(uid:int,d:ReasonIn=ReasonIn(),u:User=Depends(role("admin")),db:Session=Depends(get_db)):
    target=db.get(User,uid)
    if not target: raise HTTPException(404,"کاربر پیدا نشد")
    target.verification="REJECTED"; audit(db,u.id,"user.reject","user",uid,d.reason); db.commit(); notify(db,uid,"درخواست تأیید رد شد",d.reason or "درخواست تأیید حساب رد شد."); db.commit(); return {"verification":target.verification}

@app.post("/api/telegram/webhook/{secret}")
async def tg_webhook(secret:str,request:Request,db:Session=Depends(get_db)):
    if not secrets.compare_digest(secret,config.TG_SECRET): raise HTTPException(404)
    upd=await request.json(); cb=upd.get("callback_query")
    if not cb: return {"ok":True}
    fid=cb.get("from",{}).get("id"); msg=cb.get("message",{}); data=cb.get("data","")
    if fid not in config.ADMIN_TG_IDS:
        audit(db,f"tg:{fid}","unauthorized.callback","telegram",0,data); db.commit(); tg("answerCallbackQuery",{"callback_query_id":cb["id"],"text":"دسترسی مجاز نیست","show_alert":True}); return {"ok":True}
    parts=data.split(":")
    try:
        if len(parts)!=3: raise ValueError
        kind,act,sid=parts; actor=f"tg:{fid}"
        if kind=="pay":
            inv=db.get(Invoice,int(sid)); (approve_payment if act=="ok" else reject_payment)(db,inv,actor,"رد شده توسط ادمین از تلگرام" if act!="ok" else "")
            label="✅ پرداخت تأیید شد" if act=="ok" else "❌ پرداخت رد شد"
        elif kind=="proj":
            p=db.get(Project,int(sid))
            if act=="approve": move(p,"PUBLISHED"); move(p,"RECEIVING_PROPOSALS"); label="✅ پروژه تأیید شد"
            else: move(p,"CANCELLED"); label="❌ پروژه رد شد"
            audit(db,actor,"project."+act,"project",p.id)
        else: raise ValueError
        db.commit(); tg("editMessageText",{"chat_id":msg.get("chat",{}).get("id"),"message_id":msg.get("message_id"),"text":msg.get("text","")+f"\n\nنتیجه: {label}"}); tg("answerCallbackQuery",{"callback_query_id":cb["id"],"text":label,"show_alert":False})
    except (HTTPException,ValueError,TypeError) as e:
        db.rollback(); tg("answerCallbackQuery",{"callback_query_id":cb["id"],"text":getattr(e,"detail","عملیات نامعتبر است"),"show_alert":True})
    return {"ok":True}

@app.api_route("/",methods=["GET","HEAD"])
def home(): return FileResponse(Path(__file__).resolve().parent.parent/"frontend"/"index.html")
@app.get("/health")
def health_check(): return {"status":"ok","service":"sanaat-market"}
