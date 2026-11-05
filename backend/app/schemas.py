"""Pydantic DTOs — the OpenAPI source of truth (Week 1 frozen fields).
Field names here are the JSON field names in docs/contracts.md."""
from datetime import date, time, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_stay_dates(check_in: date | None, check_out: date | None):
    if (check_in is None) != (check_out is None):
        raise ValueError("check_in and check_out must be provided together")
    if check_in is None:
        return
    nights = (check_out - check_in).days
    if nights <= 0:
        raise ValueError("check_out must be after check_in")
    if nights > 14:
        raise ValueError("Stay cannot exceed 14 nights")

class RegisterIn(BaseModel):
    email: str; password: str = Field(min_length=8); full_name: str; role: str  # CUSTOMER | HOST

class LoginIn(BaseModel):
    email: str; password: str

class ListingIn(BaseModel):
    title: str; description: str; address: str; city: str; state: str; zip: str
    # Coordinates may be supplied directly or derived from the address by the
    # server-side geocoding provider (requirement 1.6 / 4.1).
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    price_per_night: float = Field(gt=0); max_guests: int = Field(ge=1)
    bedrooms: int = Field(ge=0); bathrooms: int = Field(ge=0)
    host_contact_name: str = ""
    host_contact_email: str = ""
    host_contact_phone: str = ""
    operating_start_time: time = time(0, 0)
    operating_end_time: time = time(23, 59)
    check_in_time: time = time(15, 0)
    check_out_time: time = time(11, 0)
    amenities: list[str] = Field(default_factory=list)
    available_times: str = "Check-in 3pm, check-out 11am"
    photos: list[str] = Field(default_factory=list)  # host-supplied photo URLs
    videos: list[str] = Field(default_factory=list)  # optional host-supplied video URLs

    @field_validator("operating_start_time", "operating_end_time", "check_in_time", "check_out_time")
    @classmethod
    def require_local_wall_clock_time(cls, value: time):
        if value.tzinfo is not None and value.utcoffset() is not None:
            raise ValueError("booking and operating times must not include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_operating_window(self):
        if self.operating_start_time == self.operating_end_time:
            raise ValueError("operating_start_time and operating_end_time must differ")
        return self

class BookingIn(BaseModel):
    listing_id: int; check_in: date; check_out: date
    check_in_time: time = time(15, 0); check_out_time: time = time(11, 0)
    guests: int = Field(ge=1)

    @field_validator("check_in_time", "check_out_time")
    @classmethod
    def require_local_wall_clock_time(cls, value: time):
        if value.tzinfo is not None and value.utcoffset() is not None:
            raise ValueError("booking times must not include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_duration(self):
        _validate_stay_dates(self.check_in, self.check_out)
        return self

class ReviewIn(BaseModel):
    booking_id: int; rating: int = Field(ge=1, le=5); comment: str = ""

class SearchQuery(BaseModel):
    check_in: date | None = None; check_out: date | None = None
    nights: int | None = Field(default=None, ge=1, le=14)
    guests: int = Field(default=1, ge=1)
    check_in_time: time | None = None; check_out_time: time | None = None
    city: str | None = None; state: str | None = None; zip: str | None = None
    address: str | None = None

    @field_validator("check_in_time", "check_out_time")
    @classmethod
    def require_local_wall_clock_time(cls, value: time | None):
        if value is not None and value.tzinfo is not None and value.utcoffset() is not None:
            raise ValueError("booking times must not include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_duration(self):
        if self.nights is not None:
            if self.check_in is None:
                raise ValueError("check_in is required when a duration is provided")
            derived_out = self.check_in + timedelta(days=self.nights)
            if self.check_out is None:
                self.check_out = derived_out
            elif self.check_out != derived_out:
                raise ValueError("check_out must equal check_in plus the requested duration")
        _validate_stay_dates(self.check_in, self.check_out)
        if (self.check_in_time is None) != (self.check_out_time is None):
            raise ValueError("check_in_time and check_out_time must be provided together")
        if self.check_in_time is not None and self.check_in is None:
            raise ValueError("dates are required when booking times are provided")
        return self
