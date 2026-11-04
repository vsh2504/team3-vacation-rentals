"""Seed loader (Week 1). Loads backend/data/listings_seed.json into an
InMemoryStore for local dev / tests. Production seed uses the same file
via a SQLAlchemy loader in Sprint 1 — same data, same IDs."""
import json, pathlib
from .domain import Listing, ListingStatus
from decimal import Decimal

def load_seed(store):
    data = json.loads((pathlib.Path(__file__).parent.parent / "data" / "listings_seed.json").read_text())
    for row in data:
        store.listings.append(Listing(
            id=row["id"], host_id=row["host_id"], title=row["title"], description=row["description"],
            address=row["address"], city=row["city"], state=row["state"], zip=row["zip"],
            lat=row["lat"], lng=row["lng"], price_per_night=Decimal(str(row["price_per_night"])),
            max_guests=row["max_guests"], bedrooms=row["bedrooms"], bathrooms=row["bathrooms"],
            amenities=row["amenities"], available_times=row["available_times"],
            status=ListingStatus(row["status"]), photos=row.get("photos", [])))
    return store
