"""CP11 - Abstract Factory (storage backends) and Builder (seed data)."""
from datetime import date
from decimal import Decimal

import pytest

from app.demo_seed import StayBuilder
from app.domain import BookingStatus, Listing, ListingStatus
from app.repositories import InMemoryStore
from app.seed import ListingBuilder, load_seed
from app.store import (InMemoryBackend, SqlBackend, StorageBackend, create_store,
                       select_backend)


# ---- Abstract Factory -------------------------------------------------------------
def test_backends_share_one_abstract_interface():
    assert issubclass(InMemoryBackend, StorageBackend) and issubclass(SqlBackend, StorageBackend)
    with pytest.raises(TypeError):
        StorageBackend()


def test_in_memory_backend_creates_store_and_flush_is_noop():
    backend = InMemoryBackend()
    store = backend.create_store()
    assert isinstance(store, InMemoryStore) and backend.kind == "memory"
    assert backend.flush(store) is None


def test_sql_backend_wraps_a_prepared_store_and_flushes_it():
    class Sql:
        flushed = 0

        def flush(self):
            Sql.flushed += 1

    sql = Sql()
    backend = SqlBackend(sql)
    assert backend.create_store() is sql and backend.kind == "sql"
    backend.flush(sql)
    assert Sql.flushed == 1


def test_select_backend_prefers_sql_then_falls_back():
    sql = object()
    assert isinstance(select_backend(lambda: sql), SqlBackend)
    assert isinstance(select_backend(lambda: None), InMemoryBackend)

    def broken():
        raise RuntimeError("no db")
    assert isinstance(select_backend(broken), InMemoryBackend)
    assert create_store(lambda: sql) is sql


def test_common_exposes_the_selected_backend():
    from app.routers import common
    assert common.BACKEND.kind in ("memory", "sql") and common.STORE is not None


# ---- Builder -----------------------------------------------------------------------
ROW = dict(id=7, host_id=2, title="T", description="d", address="a", city="c", state="CA",
           zip="95110", lat=1.5, lng=2.5, price_per_night=129.5, max_guests=4, bedrooms=2,
           bathrooms=1, amenities=["wifi"], available_times="9-5", status="APPROVED")


def test_listing_builder_builds_from_a_row_with_optional_media():
    listing = ListingBuilder(ROW).build()
    assert isinstance(listing, Listing) and listing.price_per_night == Decimal("129.5")
    assert listing.status == ListingStatus.APPROVED and listing.photos == [] and listing.videos == []
    with_media = ListingBuilder(ROW).photos(["a.jpg"]).videos(["v.mp4"]).build()
    assert with_media.photos == ["a.jpg"] and with_media.videos == ["v.mp4"]
    from_row = ListingBuilder({**ROW, "photos": ["row.jpg"]}).build()
    assert from_row.photos == ["row.jpg"]


def test_load_seed_still_loads_the_bundled_listings():
    store = load_seed(InMemoryStore())
    assert len(store.listings) == 24 and sum(l.status == ListingStatus.APPROVED for l in store.listings) == 20


def test_stay_builder_creates_a_completed_stay_in_the_past():
    listing = load_seed(InMemoryStore()).listings[0]
    booking = (StayBuilder(listing, customer_id=5).booking_id(3)
               .ending(date(2027, 1, 10), days_ago=8, nights=3).build())
    assert booking.check_out == date(2027, 1, 2) and booking.check_in == date(2026, 12, 30)
    assert booking.status == BookingStatus.COMPLETED and booking.id == 3
    assert booking.total_price == Decimal(str(listing.price_per_night)) * 3
    assert booking.guests == min(2, listing.max_guests)


def test_flush_store_delegates_to_backend_and_swallows_its_errors(monkeypatch):
    from app.routers import common

    class Exploding(InMemoryBackend):
        def flush(self, store):
            raise RuntimeError("db down")

    monkeypatch.setattr(common, "BACKEND", Exploding())
    common.flush_store(object())   # must not raise
