"""Pydantic DTOs — the OpenAPI source of truth (Week 1 frozen fields).
Field names here are the JSON field names in docs/contracts.md."""
from datetime import date
from pydantic import BaseModel, Field

class RegisterIn(BaseModel):
    email: str; password: str = Field(min_length=8); full_name: str; role: str  # CUSTOMER | HOST

class LoginIn(BaseModel):
    email: str; password: str

class ListingIn(BaseModel):
    title: str; description: str; address: str; city: str; state: str; zip: str
    lat: float; lng: float; price_per_night: float; max_guests: int = Field(ge=1)
    bedrooms: int; bathrooms: int; amenities: list[str] = []
    available_times: str = "Check-in 3pm, check-out 11am"
    photos: list[str] = []  # Sprint 2: host-supplied photo URLs; Blob upload in Sprint 3
    videos: list[str] = []  # PR 14: host-supplied video URLs

class BookingIn(BaseModel):
    listing_id: int; check_in: date; check_out: date; guests: int = Field(ge=1)

class ReviewIn(BaseModel):
    booking_id: int; rating: int = Field(ge=1, le=5); comment: str = ""

class SearchQuery(BaseModel):
    check_in: date | None = None; check_out: date | None = None; guests: int = 1
    city: str | None = None; state: str | None = None; zip: str | None = None
