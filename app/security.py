import hashlib, hmac, os, time, jwt
from collections import defaultdict
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .config import SECRET_KEY
from .db import get_db
from .models import User
def hash_pw(pw: str) -> str:
    salt = os.urandom(16); h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return salt.hex() + "$" + h.hex()
def check_pw(pw: str, stored: str) -> bool:
    salt, h = stored.split("$")
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex(), h)
def make_token(uid: int) -> str:
    return jwt.encode({"sub": str(uid), "exp": int(time.time()) + 86400}, SECRET_KEY, algorithm="HS256")
def current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "ورود لازم است")
    try: uid = int(jwt.decode(authorization[7:], SECRET_KEY, algorithms=["HS256"])["sub"])
    except Exception: raise HTTPException(401, "توکن نامعتبر است")
    u = db.get(User, uid)
    if not u or not u.is_active: raise HTTPException(401, "حساب فعال نیست")
    return u
def role(*roles):
    def dep(u: User = Depends(current_user)):
        if u.role not in roles: raise HTTPException(403, "دسترسی مجاز نیست")
        return u
    return dep
_hits = defaultdict(list)
def rate_limit(key: str, limit=10, window=60):
    t = time.time(); _hits[key] = [x for x in _hits[key] if t - x < window]
    if len(_hits[key]) >= limit: raise HTTPException(429, "تعداد درخواست بیش از حد مجاز است")
    _hits[key].append(t)
