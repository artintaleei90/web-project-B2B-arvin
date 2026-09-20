import hashlib, hmac, os, time
from collections import defaultdict
from fastapi import Depends, HTTPException, Header, Request
import jwt
from sqlalchemy.orm import Session
from .config import SECRET_KEY, TOKEN_TTL
from .db import get_db
from .models import User

def hash_pw(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 210_000)
    return salt.hex() + "$" + h.hex()

def check_pw(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
        got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 210_000).hex()
        return hmac.compare_digest(got, h)
    except (ValueError, TypeError):
        return False

def make_token(uid: int) -> str:
    now = int(time.time())
    return jwt.encode({"sub": str(uid), "iat": now, "exp": now + TOKEN_TTL}, SECRET_KEY, algorithm="HS256")

def optional_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=["HS256"])
        uid = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
    u = db.get(User, uid)
    return u if u and u.is_active else None

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "ورود لازم است")
    try:
        payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=["HS256"])
        uid = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(401, "توکن نامعتبر یا منقضی شده است")
    u = db.get(User, uid)
    if not u or not u.is_active:
        raise HTTPException(401, "حساب فعال نیست")
    return u

def role(*roles):
    def dep(u: User = Depends(current_user)):
        if u.role not in roles:
            raise HTTPException(403, "دسترسی مجاز نیست")
        return u
    return dep

_hits = defaultdict(list)
def rate_limit(key: str, limit=10, window=60):
    t = time.time()
    hits = [x for x in _hits[key] if t - x < window]
    if len(hits) >= limit:
        raise HTTPException(429, "تعداد درخواست بیش از حد مجاز است")
    hits.append(t)
    _hits[key] = hits
