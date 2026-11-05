"""Week 1 security contract. Production note: JWT signing here uses HMAC
(SHA-256) with a secret from the environment / Azure Key Vault. Passwords
use PBKDF2-HMAC-SHA256 (stdlib) in Week 1 so the domain layer has no
external dependency; the FastAPI layer may swap in passlib/bcrypt without
changing any service signature.

Pattern: Strategy. ``Pbkdf2Hasher`` and ``HmacTokenCodec`` are the default
algorithms behind ``hash_password``/``check_password`` and
``make_token``/``decode_token``; a bcrypt hasher or RS256 codec can replace
them by providing the same methods."""
import hashlib, hmac, json, os, secrets, time
from base64 import urlsafe_b64encode, urlsafe_b64decode

_DEFAULT_SECRET = "dev-only-change-in-azure-key-vault"


class Pbkdf2Hasher:
    def __init__(self, iterations: int = 100_000) -> None:
        self._iterations = iterations

    def hash(self, password: str, salt: str | None = None) -> str:
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(),
                                     self._iterations).hex()
        return f"pbkdf2:{salt}:{digest}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            _, salt, digest = stored.split(":")
            return hmac.compare_digest(self.hash(password, salt), stored)
        except Exception:
            return False


def _b64(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


class HmacTokenCodec:
    def __init__(self, secret: str | None = None) -> None:
        self._secret = secret

    def _key(self) -> str:
        return self._secret or os.environ.get("JWT_SECRET", _DEFAULT_SECRET)

    def _sign(self, h: str, p: str) -> str:
        return _b64(hmac.new(self._key().encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())

    def encode(self, user_id: int, role: str, ttl_seconds: int = 3600) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"sub": user_id, "role": role, "exp": int(time.time()) + ttl_seconds}
        h, p = _b64(json.dumps(header).encode()), _b64(json.dumps(payload).encode())
        return f"{h}.{p}.{self._sign(h, p)}"

    def decode(self, token: str) -> dict:
        h, p, sig = token.split(".")
        if not hmac.compare_digest(sig, self._sign(h, p)):
            raise ValueError("bad signature")
        payload = json.loads(urlsafe_b64decode(p + "=" * (-len(p) % 4)))
        if payload.get("exp", 0) < time.time():
            raise ValueError("expired")
        return payload


DEFAULT_HASHER = Pbkdf2Hasher()
DEFAULT_CODEC = HmacTokenCodec()


def hash_password(password: str, salt: str | None = None) -> str:
    return DEFAULT_HASHER.hash(password, salt)

def check_password(password: str, stored: str) -> bool:
    return DEFAULT_HASHER.verify(password, stored)

def make_token(user_id: int, role: str, secret: str | None = None, ttl_seconds: int = 3600) -> str:
    return HmacTokenCodec(secret).encode(user_id, role, ttl_seconds) if secret else \
        DEFAULT_CODEC.encode(user_id, role, ttl_seconds)

def decode_token(token: str, secret: str | None = None) -> dict:
    return (HmacTokenCodec(secret) if secret else DEFAULT_CODEC).decode(token)
