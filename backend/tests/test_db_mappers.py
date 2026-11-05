"""Data Mapper strategies in app.db: entity <-> row round trips."""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import db
from app.domain import (Booking, BookingStatus, Listing, ListingStatus, Review,
                        User, UserRole)

USER = User(1, "a@b.co", "hash", "Ann", UserRole.CUSTOMER, "555")
LISTING = Listing(2, 1, "Loft", "desc", "1 Main", "SJ", "CA", "95110", 37.5, -122.5,
                  Decimal("99.50"), 3, 2, 1, host_contact_name="H", host_contact_email="h@x.co",
                  host_contact_phone="555", operating_start_time=time(8),
                  operating_end_time=time(20), check_in_time=time(15), check_out_time=time(11),
                  amenities=["wifi"], available_times="anytime", status=ListingStatus.APPROVED,
                  photos=["/a.jpg"], videos=["/v.mp4"])
BOOKING = Booking(3, 2, 1, date(2030, 1, 1), date(2030, 1, 3), 2, Decimal("199.00"),
                  BookingStatus.COMPLETED, time(14), time(10), "Loft", "1 Main", "SJ", "CA",
                  "95110", 37.5, -122.5, date(2029, 12, 1),
                  datetime(2030, 1, 1, tzinfo=timezone.utc))
REVIEW = Review(4, 3, 2, 1, 5, "great")


@pytest.mark.parametrize("entity", [USER, LISTING, BOOKING, REVIEW])
def test_mapper_round_trip(entity):
    mapper = db.MAPPERS[type(entity)]
    row = mapper.to_row(entity)
    assert row["id"] == entity.id
    assert mapper.from_row(SimpleNamespace(**row)) == entity


def test_listing_row_serializes_collections_as_json_text():
    row = db.MAPPERS[Listing].to_row(LISTING)
    assert row["amenities"] == '["wifi"]' and row["photos"] == '["/a.jpg"]'
    assert row["status"] == "APPROVED" and row["price_per_night"] == Decimal("99.50")


def test_listing_mapper_tolerates_rows_without_videos_column():
    row = db.MAPPERS[Listing].to_row(LISTING)
    row.pop("videos")
    assert db.MAPPERS[Listing].from_row(SimpleNamespace(**row)).videos == []


def test_every_mapper_targets_its_table():
    assert {m.table.name for m in db.MAPPERS.values()} == {"users", "listings", "bookings", "reviews"}


def test_unsupported_entity_is_rejected(tmp_path):
    from sqlalchemy import create_engine
    store = db.SqlBackedStore(create_engine(f"sqlite:///{tmp_path / 'x.db'}", future=True))
    with pytest.raises(TypeError, match="Unsupported"):
        store.persist(object())


def test_postgres_extension_preparation_enables_btree_gist():
    conn = MagicMock()
    db._enable_extensions(conn, "postgresql")
    statements = [str(call.args[0]) for call in conn.execute.call_args_list]
    assert any("btree_gist" in text for text in statements)


def test_sqlite_extension_preparation_skips_extensions():
    conn = MagicMock()
    db._enable_extensions(conn, "sqlite")
    conn.execute.assert_not_called()
