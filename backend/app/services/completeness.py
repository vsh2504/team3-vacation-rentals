"""Listing completeness report used by the administrator moderation queue.

The queue needs enough evidence to assess accuracy before approving, so this
reports the individual checks as well as a percentage score. Media may be
photos or videos (requirement 1.3); contact information may be any of name,
email, or phone.
"""
from ..domain import Listing


def _text(value) -> bool:
    return bool(str(value or "").strip())


def listing_completeness(listing: Listing) -> dict:
    photos = list(getattr(listing, "photos", None) or [])
    videos = list(getattr(listing, "videos", None) or [])
    contact = any(_text(value) for value in (
        listing.host_contact_name, listing.host_contact_email, listing.host_contact_phone))
    checks = {
        "title": _text(listing.title),
        "description": _text(listing.description),
        "address": _text(listing.address),
        "city": _text(listing.city),
        "state": _text(listing.state),
        "zip": _text(listing.zip),
        "coordinates": listing.lat is not None and listing.lng is not None,
        "price_per_night": bool(listing.price_per_night and listing.price_per_night > 0),
        "max_guests": bool(listing.max_guests and listing.max_guests >= 1),
        "amenities": bool(listing.amenities),
        "available_times": _text(listing.available_times),
        "operating_hours": listing.operating_start_time != listing.operating_end_time,
        "contact": contact,
        "media": bool(photos or videos),
    }
    missing = [name for name, present in checks.items() if not present]
    return {
        "complete": not missing,
        "score": round(100 * (len(checks) - len(missing)) / len(checks)),
        "missing": missing,
        "checks": checks,
        "photo_count": len(photos),
        "video_count": len(videos),
        "has_photos": bool(photos),
        "has_videos": bool(videos),
    }
