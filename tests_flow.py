from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import User
from app.security import hash_pw
c = TestClient(app); H = lambda t: {"Authorization": "Bearer " + t}
db = SessionLocal()
if not db.query(User).filter_by(email="a@x.com").first(): db.add(User(email="a@x.com", password_hash=hash_pw("Admin12345"), role="admin")); db.commit()
def reg(e, r, **k): return c.post("/api/auth/register", json={"email": e, "password": "Passw0rd123", "role": r, "name": "نام تست", "city": "تهران", **k})
cu = reg("c@x.com", "customer").json()["token"]; pv = reg("p@x.com", "provider", kind="contractor").json()["token"]
ad = c.post("/api/auth/login", json={"email": "a@x.com", "password": "Admin12345"}).json()["token"]
p = c.post("/api/projects", headers=H(cu), json={"title": "سوله صنعتی", "category_id": 1, "city": "تهران", "description": "احداث سوله ۱۰۰۰ متری تماس 09121234567", "budget_min": 1, "budget_max": 5, "duration_days": 30}).json(); print(p)
assert c.post(f"/api/projects/{p['id']}/proposals", headers=H(pv), json={"price": 10, "duration_days": 5, "description": "پیشنهاد کامل"}).status_code == 404
print(c.post(f"/api/admin/projects/{p['id']}/approve", headers=H(cu)).status_code, "(expect 403)")
c.post(f"/api/admin/projects/{p['id']}/approve", headers=H(ad))
pr = c.post(f"/api/projects/{p['id']}/proposals", headers=H(pv), json={"price": 10, "duration_days": 5, "description": "پیشنهاد کامل"}).json()
assert c.post(f"/api/projects/{p['id']}/proposals", headers=H(pv), json={"price": 10, "duration_days": 5, "description": "پیشنهاد کامل"}).status_code == 409
cid = c.post(f"/api/proposals/{pr['id']}/select", headers=H(cu)).json()["connection_id"]
print(c.post(f"/api/connections/{cid}/accept", headers=H(pv)).json())
print(c.post(f"/api/connections/{cid}/messages", headers=H(cu), json={"body": "زنگ بزن 0912 123 4567 یا @ali_test"}).json())
print(c.get(f"/api/connections/{cid}/contact", headers=H(cu)).status_code, "(expect 403)")
inv = c.post(f"/api/connections/{cid}/invoice", headers=H(cu)).json(); print(inv)
iid = db.query(__import__("app.models", fromlist=["Invoice"]).Invoice).first().id
print(c.post(f"/api/admin/invoices/{iid}/approve", headers=H(cu)).status_code, "(expect 403)")
print(c.post(f"/api/admin/invoices/{iid}/approve", headers=H(ad)).json())
print(c.get(f"/api/connections/{cid}/contact", headers=H(cu)).status_code, "(expect 200)")
k = {"terms": "شرایط کامل قرارداد بین طرفین", "start_date": "1405-07-01", "end_date": "1405-08-01"}
c.put(f"/api/connections/{cid}/contract", headers=H(cu), json=k); c.post(f"/api/connections/{cid}/contract/accept", headers=H(cu)); print(c.post(f"/api/connections/{cid}/contract/accept", headers=H(pv)).json())
print(c.post(f"/api/admin/contracts/1/approve", headers=H(ad)).json())
print(c.post(f"/api/connections/{cid}/cancel", headers=H(cu)).status_code, "(expect 403)")
c.post(f"/api/connections/{cid}/complete", headers=H(cu)); print(c.post(f"/api/connections/{cid}/complete", headers=H(pv)).json())
print(c.post(f"/api/projects/{p['id']}/reviews", headers=H(cu), json={"rating": 5}).json())
