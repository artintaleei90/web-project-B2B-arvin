"""python seed_admin.py admin@example.com 'StrongPass123'"""
import sys
from app.db import SessionLocal
from app.models import User
from app.security import hash_pw
db = SessionLocal(); db.add(User(email=sys.argv[1].lower(), password_hash=hash_pw(sys.argv[2]), role="admin", verification="VERIFIED")); db.commit(); print("admin created")
