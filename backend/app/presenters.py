"""Presenters: turn domain objects into the JSON shapes the API contract defines.

Routers stay thin (validate -> call service -> present); every response shape
is built here once, so the Search, Booking and Admin screens cannot drift.

Pattern: Presenter (domain -> JSON shape).
"""
from datetime import date, time
from decimal import Decimal

from .domain import BookingStatus, ListingStatus, booked_today
from .geocoding import osm_embed_url, osm_url
from .services import ListingService
from .services.completeness import listing_completeness


def format_clock(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def stay_state(booking, today: date) -> str:
    if booking.status == BookingStatus.CANCELLED:
        return "cancelled"
    return "past" if booking.check_out <= today else "upcoming"


def booking_out(b, store, today: date) -> dict:
    listing = next((item for item in store.listings if item.id == b.listing_id), None)
    has_point = b.location_lat is not None and b.location_lng is not None
    map_url = osm_url(b.location_lat, b.location_lng) if has_point else None
    embed_url = osm_embed_url(b.location_lat, b.location_lng) if has_point else None
    return {"id": b.id, "listing_id": b.listing_id, "customer_id": b.customer_id,
            "check_in": str(b.check_in), "check_out": str(b.check_out), "guests": b.guests,
            "check_in_time": format_clock(b.check_in_time),
            "check_out_time": format_clock(b.check_out_time),
            "total_price": str(b.total_price), "status": b.status.value,
            "stay_state": stay_state(b, today),
            "has_review": any(r.booking_id == b.id for r in store.reviews),
            "booked_date": str(b.booked_date),
            "cancelled_at": b.cancelled_at.isoformat() if b.cancelled_at else None,
            "location": {"name": b.location_name, "address": b.location_address,
                         "city": b.location_city, "state": b.location_state,
                         "zip": b.location_zip, "lat": b.location_lat,
                         "lng": b.location_lng, "map_url": map_url,
                         "osm_embed_url": embed_url},
            "map_url": map_url,
            "listing": {"id": b.listing_id,
                        "title": b.location_name or (listing.title if listing else ""),
                        "price_per_night": str(listing.price_per_night) if listing else None,
                        "max_guests": listing.max_guests if listing else None,
                        "photos": listing.photos if listing else [],
                        "url": f"/listings/{b.listing_id}"}}


def host_booking_out(b, store, today: date, listing, customers: dict, review) -> dict:
    """A booking as the owning host sees it: customer identity plus any review."""
    row = booking_out(b, store, today)
    customer = customers.get(b.customer_id)
    row["listing"] = {"id": listing.id, "title": listing.title, "city": listing.city,
                      "state": listing.state, "zip": listing.zip,
                      "photos": listing.photos, "url": f"/listings/{listing.id}"}
    row["customer"] = {"id": b.customer_id,
                       "full_name": customer.full_name if customer else "Unknown",
                       "email": customer.email if customer else ""}
    row["review"] = ({"id": review.id, "rating": review.rating, "comment": review.comment}
                     if review else None)
    return row


def reviewer_name(store, customer_id) -> str:
    """First name and last initial only; never the email."""
    user = next((u for u in store.users if u.id == customer_id), None)
    parts = (user.full_name if user else "").split()
    if not parts:
        return "Guest"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


def host_out(store, host_id: int) -> dict | None:
    host = next((u for u in store.users if u.id == host_id), None)
    if not host:
        return None
    return {"id": host.id, "full_name": host.full_name, "email": host.email,
            "phone": host.phone, "role": host.role.value}


def admin_listing_out(listing, store) -> dict:
    """Moderation record: everything needed to assess completeness/accuracy."""
    completeness = listing_completeness(listing)
    return {
        "id": listing.id,
        "host_id": listing.host_id,
        "host": host_out(store, listing.host_id),
        "title": listing.title,
        "description": listing.description,
        "address": listing.address,
        "city": listing.city,
        "state": listing.state,
        "zip": listing.zip,
        "lat": listing.lat,
        "lng": listing.lng,
        "price_per_night": str(listing.price_per_night),
        "max_guests": listing.max_guests,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "amenities": listing.amenities,
        "available_times": listing.available_times,
        "host_contact_name": listing.host_contact_name,
        "host_contact_email": listing.host_contact_email,
        "host_contact_phone": listing.host_contact_phone,
        "operating_start_time": format_clock(listing.operating_start_time),
        "operating_end_time": format_clock(listing.operating_end_time),
        "check_in_time": format_clock(listing.check_in_time),
        "check_out_time": format_clock(listing.check_out_time),
        "photos": listing.photos,
        "videos": listing.videos,
        "status": listing.status.value,
        "searchable": listing.status == ListingStatus.APPROVED,
        "completeness": completeness,
        "photo_count": completeness["photo_count"],
        "video_count": completeness["video_count"],
    }


def listing_out(listing, store, today: date, *, nights: int | None = None,
                 distance: float | None = None, availability: dict | None = None) -> dict:
    service = ListingService(store)
    reviews = service.review_summary(listing.id)
    availability = availability or service.availability(listing)
    night_count = availability.get("nights") if availability.get("nights") is not None else nights
    total_cost = availability.get("total_cost")
    if total_cost is None and night_count is not None:
        total_cost = str(Decimal(str(listing.price_per_night)) * Decimal(night_count))
    return {
        "id": listing.id,
        "host_id": listing.host_id,
        "title": listing.title,
        "description": listing.description,
        "address": listing.address,
        "city": listing.city,
        "state": listing.state,
        "zip": listing.zip,
        "lat": listing.lat,
        "lng": listing.lng,
        "price_per_night": str(listing.price_per_night),
        "nightly_price": str(listing.price_per_night),
        "price_tier": service.price_tier(listing),
        "currency": "USD",
        "max_guests": listing.max_guests,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "amenities": listing.amenities,
        "available_times": listing.available_times,
        "host_contact_name": listing.host_contact_name,
        "host_contact_email": listing.host_contact_email,
        "host_contact_phone": listing.host_contact_phone,
        "operating_start_time": format_clock(listing.operating_start_time),
        "operating_end_time": format_clock(listing.operating_end_time),
        "check_in_time": format_clock(listing.check_in_time),
        "check_out_time": format_clock(listing.check_out_time),
        "status": listing.status.value,
        "photos": listing.photos,
        "videos": listing.videos,
        "average_rating": reviews["average_rating"],
        "review_count": reviews["review_count"],
        "reviews": reviews["reviews"],
        "booked_today": booked_today(listing.id, store.bookings, today),
        "nights": night_count,
        "duration_nights": night_count,
        "total_cost": total_cost,
        "available": bool(availability.get("available")),
        "is_available": bool(availability.get("available")),
        "availability": availability,
        "distance_km": distance,
        "map_url": osm_url(listing.lat, listing.lng),
        "osm_embed_url": osm_embed_url(listing.lat, listing.lng),
        "map_embed_url": osm_embed_url(listing.lat, listing.lng),
        "listing_url": f"/listings/{listing.id}",
    }
