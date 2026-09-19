from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint, Float
from .db import Base
now = datetime.utcnow
def pk(): return Column(Integer, primary_key=True)
class User(Base):
    __tablename__ = "users"
    id = pk(); email = Column(String(190), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="customer")  # customer|provider|admin
    verification = Column(String(20), default="UNVERIFIED")  # UNVERIFIED|PENDING|VERIFIED|REJECTED
    is_active = Column(Boolean, default=True); created_at = Column(DateTime, default=now)
    phone = Column(String(30)); telegram = Column(String(60))  # exposed only after payment approval
class ProviderProfile(Base):
    __tablename__ = "provider_profiles"
    id = pk(); user_id = Column(ForeignKey("users.id"), unique=True)
    name = Column(String(160)); kind = Column(String(30))  # contractor|manufacturer|service|custom|other
    city = Column(String(80)); specialty = Column(String(160)); bio = Column(Text)
    experience_years = Column(Integer, default=0); rating = Column(Float, default=0); rating_count = Column(Integer, default=0)
    completed_projects = Column(Integer, default=0); free_used = Column(Integer, default=0)
    plan = Column(String(20), default="FREE")
class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    id = pk(); user_id = Column(ForeignKey("users.id"), unique=True)
    name = Column(String(160)); city = Column(String(80)); field = Column(String(160))
    rating = Column(Float, default=0); rating_count = Column(Integer, default=0)
class Category(Base):
    __tablename__ = "categories"
    id = pk(); slug = Column(String(80), unique=True); name = Column(String(120)); parent_id = Column(ForeignKey("categories.id"))
    kind = Column(String(30), default="provider")  # extensible: provider | workforce ...
class Service(Base):
    __tablename__ = "services"
    id = pk(); slug = Column(String(120), unique=True); title = Column(String(160)); category_id = Column(ForeignKey("categories.id"))
    description = Column(Text)
class Project(Base):
    __tablename__ = "projects"
    id = pk(); customer_id = Column(ForeignKey("users.id"), index=True); category_id = Column(ForeignKey("categories.id"))
    title = Column(String(200)); description = Column(Text); city = Column(String(80), index=True)
    budget_min = Column(Integer); budget_max = Column(Integer); duration_days = Column(Integer)
    requirements = Column(Text); status = Column(String(30), default="PENDING_REVIEW", index=True)
    selected_provider_id = Column(ForeignKey("users.id")); created_at = Column(DateTime, default=now)
class Proposal(Base):
    __tablename__ = "proposals"
    id = pk(); project_id = Column(ForeignKey("projects.id"), index=True); provider_id = Column(ForeignKey("users.id"))
    price = Column(Integer); duration_days = Column(Integer); description = Column(Text)
    status = Column(String(20), default="ACTIVE")  # ACTIVE|CANCELLED|SELECTED|REJECTED
    created_at = Column(DateTime, default=now)
class Connection(Base):
    __tablename__ = "connections"
    id = pk(); project_id = Column(ForeignKey("projects.id"), index=True); proposal_id = Column(ForeignKey("proposals.id"))
    customer_id = Column(ForeignKey("users.id")); provider_id = Column(ForeignKey("users.id"))
    status = Column(String(20), default="PENDING")  # PENDING|ACCEPTED|CANCELLED
    contact_unlocked = Column(Boolean, default=False); created_at = Column(DateTime, default=now)
class Message(Base):
    __tablename__ = "messages"
    id = pk(); connection_id = Column(ForeignKey("connections.id"), index=True); sender_id = Column(ForeignKey("users.id"))
    body = Column(Text); redacted = Column(Boolean, default=False); created_at = Column(DateTime, default=now)
class Invoice(Base):
    __tablename__ = "invoices"
    id = pk(); number = Column(String(30), unique=True); n_code = Column(String(20), unique=True)
    connection_id = Column(ForeignKey("connections.id"), index=True); project_id = Column(ForeignKey("projects.id"))
    amount = Column(Integer); status = Column(String(20), default="AWAITING_PAYMENT")  # AWAITING_PAYMENT|PAID|REJECTED
    reject_reason = Column(Text); tg_message_id = Column(Integer); created_at = Column(DateTime, default=now)
class Payment(Base):
    __tablename__ = "payments"
    id = pk(); invoice_id = Column(ForeignKey("invoices.id")); decided_by = Column(String(60))
    result = Column(String(20)); reason = Column(Text); created_at = Column(DateTime, default=now)
class Contract(Base):
    __tablename__ = "contracts"
    id = pk(); connection_id = Column(ForeignKey("connections.id"), unique=True); project_id = Column(ForeignKey("projects.id"))
    terms = Column(Text); amount = Column(Integer); start_date = Column(String(20)); end_date = Column(String(20))
    customer_accepted = Column(Boolean, default=False); provider_accepted = Column(Boolean, default=False)
    status = Column(String(20), default="DRAFT")  # DRAFT|REVIEW|RETURNED|APPROVED
    admin_note = Column(Text); customer_done = Column(Boolean, default=False); provider_done = Column(Boolean, default=False)
class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("project_id", "author_id"),)
    id = pk(); project_id = Column(ForeignKey("projects.id")); author_id = Column(ForeignKey("users.id"))
    target_id = Column(ForeignKey("users.id")); rating = Column(Integer); body = Column(Text); created_at = Column(DateTime, default=now)
class Notification(Base):
    __tablename__ = "notifications"
    id = pk(); user_id = Column(ForeignKey("users.id"), index=True); event = Column(String(60)); text = Column(Text)
    read = Column(Boolean, default=False); created_at = Column(DateTime, default=now)
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = pk(); user_id = Column(ForeignKey("users.id")); plan = Column(String(20)); active_until = Column(DateTime)
class Report(Base):
    __tablename__ = "reports"
    id = pk(); reporter_id = Column(ForeignKey("users.id")); target_type = Column(String(30)); target_id = Column(Integer)
    reason = Column(Text); status = Column(String(20), default="OPEN"); created_at = Column(DateTime, default=now)
class Dispute(Base):
    __tablename__ = "disputes"
    id = pk(); project_id = Column(ForeignKey("projects.id")); opened_by = Column(ForeignKey("users.id"))
    reason = Column(Text); status = Column(String(20), default="OPEN"); created_at = Column(DateTime, default=now)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = pk(); actor = Column(String(60)); action = Column(String(80)); entity = Column(String(60)); entity_id = Column(Integer)
    detail = Column(Text); created_at = Column(DateTime, default=now)
