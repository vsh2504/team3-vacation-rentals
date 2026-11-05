"""Host media upload. POST /uploads (HOST only) with the raw file as the request
body and Content-Type image/jpeg|png|webp|gif or video/mp4|webm. The type is
verified against the file's magic bytes, not just the header. Files are stored
under STAYNEST_UPLOAD_DIR and served at /uploads/<name>; the returned `url` is
a site-relative path accepted by ListingIn.photos / ListingIn.videos.

Pattern: Strategy (per-content-type signature checks) behind a thin Controller."""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from ..core.errors import ApiError, ok
from ..domain import UserRole
from .common import get_current_user

router = APIRouter(tags=["uploads"])

UPLOAD_DIR = Path(os.environ.get("STAYNEST_UPLOAD_DIR")
                  or Path(__file__).resolve().parents[2] / "uploads")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
_TYPES = {  # content-type -> (extension, kind)
    "image/jpeg": (".jpg", "photo"), "image/png": (".png", "photo"),
    "image/webp": (".webp", "photo"), "image/gif": (".gif", "photo"),
    "video/mp4": (".mp4", "video"), "video/webm": (".webm", "video"),
}


def _starts_with(prefix: bytes):
    return lambda data: data.startswith(prefix)


# Strategy: one signature check per content type (magic bytes).
_SIGNATURES = {
    "image/jpeg": _starts_with(b"\xff\xd8\xff"),
    "image/png": _starts_with(b"\x89PNG\r\n\x1a\n"),
    "image/gif": lambda data: data[:6] in (b"GIF87a", b"GIF89a"),
    "image/webp": lambda data: data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    "video/mp4": lambda data: data[4:8] == b"ftyp",
    "video/webm": _starts_with(b"\x1a\x45\xdf\xa3"),
}


def _matches_signature(content_type: str, data: bytes) -> bool:
    check = _SIGNATURES.get(content_type)
    return bool(check and check(data))


@router.post("/uploads")
async def upload_media(request: Request, user=Depends(get_current_user)):
    if user.role != UserRole.HOST:
        raise ApiError("FORBIDDEN", "Only hosts can upload listing media")
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type not in _TYPES:
        raise ApiError("VALIDATION_ERROR",
                       "Unsupported file type; use JPEG, PNG, WebP, GIF, MP4 or WebM", "file")
    ext, kind = _TYPES[content_type]
    limit = MAX_IMAGE_BYTES if kind == "photo" else MAX_VIDEO_BYTES
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise ApiError("VALIDATION_ERROR", f"File too large (max {limit // 1024 // 1024} MB)", "file")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > limit:
            raise ApiError("VALIDATION_ERROR", f"File too large (max {limit // 1024 // 1024} MB)", "file")
    if not data:
        raise ApiError("VALIDATION_ERROR", "Empty file", "file")
    if not _matches_signature(content_type, bytes(data)):
        raise ApiError("VALIDATION_ERROR", "File contents do not match its declared type", "file")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / name).write_bytes(data)
    return ok({"url": f"/uploads/{name}", "kind": kind, "content_type": content_type,
               "size": len(data)})
