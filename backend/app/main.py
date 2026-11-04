"""FastAPI entrypoint — Core APIs mounted by owner.
See docs/feature-breakdown.md § Core APIs.
  auth.py + admin.py      — Ranadhir Reddy Rikkala (Identity & Admin)
  listings.py             — Vinayak Gupta (Search & Listings)
  bookings.py             — Manoj (Booking)
  reviews.py + analytics.py — Prajval Sudhir (Reviews & Analytics)
Routers validate (Pydantic), services enforce rules, repositories persist.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .core.errors import ApiError
from .routers import admin, analytics, auth, bookings, listings, reviews

app = FastAPI(title="StayNest API", version="0.2.0-core-apis")

@app.exception_handler(ApiError)
async def api_error_handler(_, exc: ApiError):
    return JSONResponse(status_code=exc.status, content=exc.envelope())

@app.get("/health")
def health():
    return {"success": True, "data": {"status": "ok", "version": "0.2.0-core-apis"}, "error": None}

# Core APIs, one router per agent — see each router file's header.
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(listings.router)
app.include_router(bookings.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
