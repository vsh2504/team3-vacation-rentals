"""Week 1 security contract. Production note: JWT signing here uses HMAC
(SHA-256) with a secret from the environment / Azure Key Vault. Passwords
use PBKDF2-HMAC-SHA256 (stdlib) in Week 1 so the domain layer has no
external dependency; the FastAPI layer may swap in passlib/bcrypt without
changing any service signature."""
import hashlib, hmac, json, os, secrets, time
from base64 import urlsafe_b64encode, urlsafe_b64decode

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"pbkdf2:{salt}:{digest}"

def check_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split(":")
        return hmac.compare_digest(hash_password(password, salt), stored)
    except Exception:
        return False

def _b64(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()

def make_token(user_id: int, role: str, secret: str | None = None, ttl_seconds: int = 3600) -> str:
    secret = secret or os.environ.get("JWT_SECRET", "dev-only-change-in-azure-key-vault")
    header, payload = {"alg": "HS256", "typ": "JWT"}, {"sub": user_id, "role": role, "exp": int(time.time()) + ttl_seconds}
    h, p = _b64(json.dumps(header).encode()), _b64(json.dumps(payload).encode())
    sig = _b64(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"

def decode_token(token: str, secret: str | None = None) -> dict:
    secret = secret or os.environ.get("JWT_SECRET", "dev-only-change-in-azure-key-vault")
    h, p, sig = token.split(".")
    expected = _b64(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise ValueError("bad signature")
    payload = json.loads(urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    if payload.get("exp", 0) < time.time():
        raise ValueError("expired")
    return payload
