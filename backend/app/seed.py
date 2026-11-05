"""Seed loader (Week 1). Pattern: Builder. Loads backend/data/listings_seed.json into an
InMemoryStore for local dev / tests. Production seed uses the same file
via a SQLAlchemy loader in Sprint 1 — same data, same IDs."""
import json, pathlib
from .domain import Listing, ListingStatus
from decimal import Decimal

class ListingBuilder:
    """Pattern: Builder - assembles a seed ``Listing`` step by step from a JSON row."""

    def __init__(self, row: dict) -> None:
        self._row = row
        self._photos = list(row.get("photos", []))
        self._videos = list(row.get("videos", []))

    def photos(self, photos: list[str]) -> "ListingBuilder":
        self._photos = list(photos)
        return self

    def videos(self, videos: list[str]) -> "ListingBuilder":
        self._videos = list(videos)
        return self

    def build(self) -> Listing:
        row = self._row
        return Listing(
            id=row["id"], host_id=row["host_id"], title=row["title"], description=row["description"],
            address=row["address"], city=row["city"], state=row["state"], zip=row["zip"],
            lat=row["lat"], lng=row["lng"], price_per_night=Decimal(str(row["price_per_night"])),
            max_guests=row["max_guests"], bedrooms=row["bedrooms"], bathrooms=row["bathrooms"],
            amenities=row["amenities"], available_times=row["available_times"],
            status=ListingStatus(row["status"]), photos=self._photos, videos=self._videos)


def load_seed(store):
    data = json.loads((pathlib.Path(__file__).parent.parent / "data" / "listings_seed.json").read_text())
    for row in data:
        store.listings.append(ListingBuilder(row).build())
    return store
