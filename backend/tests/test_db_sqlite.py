"""SqlBackedStore characterization tests on SQLite (no external database)."""
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from app import db
from app.core.errors import ApiError
from app.domain import (Booking, BookingStatus, Listing, ListingStatus, Review,
                        User, UserRole)


@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def store(engine):
    return db.SqlBackedStore(engine)


def test_first_run_seeds_users_listings_and_demo_reviews(store):
    assert {u.id for u in store.users} >= {1, 2, 3, 4, 99}
    assert len(store.listings) == 24
    assert all(l.host_contact_email.endswith("@staynest.local") for l in store.listings)
    assert any(u.email == "customer1@staynest.local" for u in store.users)
    assert store.reviews and store.bookings


def test_second_start_reloads_persisted_rows_without_reseeding(engine):
    first = db.SqlBackedStore(engine)
    counts = (len(first.users), len(first.listings), len(first.bookings), len(first.reviews))
    second = db.SqlBackedStore(engine)
    assert (len(second.users), len(second.listings),
            len(second.bookings), len(second.reviews)) == counts
    listing = second.listings[0]
    assert isinstance(listing.price_per_night, Decimal) and isinstance(listing.lat, float)
    assert isinstance(listing.amenities, list) and listing.status in ListingStatus
    assert isinstance(second.bookings[0].total_price, Decimal)


def test_save_persists_every_entity_type(engine, store):
    user = store.save(User(500, "n@x.co", "h", "New", UserRole.CUSTOMER, "555"))
    listing = store.listings[0]
    booking = store.save(Booking(
        900, listing.id, user.id, date(2030, 1, 1), date(2030, 1, 3), 2, Decimal("200"),
        booked_date=date(2029, 12, 1), cancelled_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        check_in_time=time(14), check_out_time=time(10)))
    review = store.save(Review(900, booking.id, listing.id, user.id, 5, "great"))
    clone = db.SqlBackedStore(engine)
    assert next(u for u in clone.users if u.id == 500).phone == "555"
    got = next(b for b in clone.bookings if b.id == 900)
    # location snapshot is captured from the listing at persist time
    assert got.location_zip == listing.zip and got.location_lat == pytest.approx(listing.lat)
    assert got.check_in_time == time(14) and got.cancelled_at is not None
    assert next(r for r in clone.reviews if r.id == 900).comment == "great"
    assert review.rating == 5


def test_booking_snapshot_is_kept_when_already_present(store):
    listing = store.listings[0]
    b = store.save(Booking(901, listing.id, 1, date(2030, 2, 1), date(2030, 2, 2), 1,
                           Decimal("1"), booked_date=date(2030, 1, 1),
                           location_address="custom", location_name="n"))
    assert b.location_address == "custom"
    orphan = store.save(Booking(902, 424242, 1, date(2030, 3, 1), date(2030, 3, 2), 1,
                                Decimal("1"), booked_date=date(2030, 1, 1)))
    assert orphan.location_address == ""


def test_flush_upserts_in_place_mutations(engine, store):
    listing = store.listings[0]
    listing.title = "Renamed"
    listing.status = ListingStatus.REMOVED
    store.flush()
    clone = db.SqlBackedStore(engine)
    reloaded = next(l for l in clone.listings if l.id == listing.id)
    assert reloaded.title == "Renamed" and reloaded.status == ListingStatus.REMOVED


def test_duplicate_booking_and_review_map_to_conflicts(store):
    listing = store.listings[0]
    b = Booking(903, listing.id, 1, date(2030, 4, 1), date(2030, 4, 2), 1, Decimal("1"),
                booked_date=date(2030, 1, 1))
    store.save(b)
    with pytest.raises(ApiError) as e:
        store.save(Booking(903, listing.id, 1, date(2030, 5, 1), date(2030, 5, 2), 1,
                           Decimal("1"), booked_date=date(2030, 1, 1)))
    assert e.value.code == "CONFLICT"
    store.save(Review(950, 903, listing.id, 1, 4))
    with pytest.raises(ApiError) as e:
        store.save(Review(951, 903, listing.id, 1, 4))
    assert e.value.code == "CONFLICT" and "One review" in e.value.message


def test_other_integrity_errors_propagate(store):
    with pytest.raises(IntegrityError):
        store.save(User(777, store.users[0].email, "h", "Dup", UserRole.HOST))


def test_constraint_name_translation_for_postgres_style_errors(store):
    class Diag: constraint_name = "excl_bookings_confirmed_overlap"
    class Orig(Exception): diag = Diag()
    exc = IntegrityError("stmt", {}, Orig("boom"))
    assert db._constraint_name(exc) == "excl_bookings_confirmed_overlap"
    assert db._constraint_name(IntegrityError("s", {}, Exception("x"))) is None

    booking = Booking(1, 1, 1, date(2030, 1, 1), date(2030, 1, 2), 1, Decimal("1"))
    def raise_pg(*a, **k): raise exc
    store._persist = raise_pg
    with pytest.raises(ApiError) as e:
        store.persist(booking)
    assert e.value.code == "CONFLICT"

    class ReviewDiag: constraint_name = "uq_reviews_booking"
    class ReviewOrig(Exception): diag = ReviewDiag()
    review_exc = IntegrityError("stmt", {}, ReviewOrig("dup"))
    def raise_review(*a, **k): raise review_exc
    store._persist = raise_review
    with pytest.raises(ApiError):
        store.persist(Review(1, 1, 1, 1, 5))
    with pytest.raises(IntegrityError):
        store.persist(User(1, "e", "h", "n", UserRole.HOST))


def test_make_store_and_flush_store(monkeypatch, tmp_path):
    monkeypatch.delenv("STAYNEST_DB_URL", raising=False)
    assert db.get_db_url() == "" and db.make_store() is None
    monkeypatch.setenv("STAYNEST_DB_URL", f"sqlite:///{tmp_path / 'm.db'}")
    sql_store = db.make_store()
    assert isinstance(sql_store, db.SqlBackedStore)
    sql_store.listings[0].title = "Flushed"
    db.flush_store(sql_store)
    db.flush_store(object())          # no flush attribute -> no-op
    assert db.SqlBackedStore(sql_store._engine).listings[0].title == "Flushed"


def test_review_mapper_tolerates_null_comment():
    class Row:
        def __init__(self, **kw): self.__dict__.update(kw)
    review = db.MAPPERS[Review].from_row(Row(id=1, booking_id=1, listing_id=1, customer_id=1,
                                             rating=5, comment=None))
    assert review.comment == ""


def test_flush_inserts_rows_added_directly_to_memory(engine, store):
    store.users.append(User(600, "direct@x.co", "h", "Direct", UserRole.CUSTOMER))
    store.flush()
    assert any(u.id == 600 for u in db.SqlBackedStore(engine).users)
