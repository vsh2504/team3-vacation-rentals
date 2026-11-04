"""Sprint 3, US31 — parallel booking race test.
Usage: python3 scripts/load_test.py [base_url] [workers]
Uses the live API (default http://localhost:8000) with TestClient-style
HTTP: registers one customer, then fires N parallel bookings for the
same listing/dates. Exactly one must succeed (201/200), the rest 409.
This proves the overlap check holds under concurrency at the API level.
Note: the in-memory store is single-process; a multi-instance VMSS
deployment needs a DB-level unique/transaction guard — see infra/azure/README.md.
"""
import concurrent.futures, json, sys, urllib.request
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")

_, me = call("POST", "/auth/register", body={"email": "race@staynest.test", "password": "password123", "full_name": "Race", "role": "CUSTOMER"})
if me.get("error"):  # already registered from a previous run
    pass
_, login = call("POST", "/auth/login", body={"email": "race@staynest.test", "password": "password123"})
tok = login["data"]["access_token"]
_, listings = call("GET", "/listings/search?zip=95110")
lid = listings["data"][0]["id"]
payload = {"listing_id": lid, "check_in": "2027-06-01", "check_out": "2027-06-03", "guests": 2}
with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
    results = list(ex.map(lambda _: call("POST", "/bookings", token=tok, body=payload), range(N)))
codes = [c for c, _ in results]
print(f"workers={N} listing={lid} codes={codes} successes={codes.count(200)} conflicts={codes.count(409)}")
assert codes.count(200) == 1, "Race test failed: expected exactly one successful booking"
print("PASS: no double-booking under parallel attempts")
