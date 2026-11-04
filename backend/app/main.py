"""FastAPI entrypoint — Week 1 skeleton. Routers validate (Pydantic),
services enforce rules, repositories persist. Full route wiring is
Sprint 1; Week 1 proves /health + the error envelope + the domain tests."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .core.errors import ApiError

app = FastAPI(title="StayNest API", version="0.1.0-week1")

@app.exception_handler(ApiError)
async def api_error_handler(_, exc: ApiError):
    return JSONResponse(status_code=exc.status, content=exc.envelope())

@app.get("/health")
def health():
    return {"success": True, "data": {"status": "ok", "version": "0.1.0-week1"}, "error": None}

# Sprint 1 routers (to be mounted here, one per slice):
#   auth.py (A), listings.py + search.py (B), bookings.py (C),
#   reviews.py + admin.py + analytics.py (D)
# They must import only from domain.py / services.py / repositories.py.
