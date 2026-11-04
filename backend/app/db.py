"""Sprint 3 — Database persistence (opt-in, write-through).

Default dev mode is still the in-memory store (see routers/common.py),
so `uvicorn app.main:app` works with zero setup and all Week 1 tests
pass without a database.

Set STAYNEST_DB_URL to use a real database, e.g.:
  STAYNEST_DB_URL=sqlite:///./staynest.db
  STAYNEST_DB_URL=postgresql://staynest:staynest@localhost:5432/staynest

How it works: SqlBackedStore is an InMemoryStore that, on startup,
loads its lists from the DB, and on every save() also upserts that row
to the DB. Mutations that happen in place (approve, cancel, complete,
edit, remove) call flush_store() from the router — see routers/common.py
— which upserts every row. Services never see SQL; they only see the
same store interface as Week 1.

Tables are created by create_tables() and match
backend/db/migrations/001_init.sql exactly, so the same schema can be
applied to Azure Database for PostgreSQL by running that SQL file
(US31) without running this Python code.
"""
import json
import os
from datetime import date
from decimal import Decimal

from sqlalchemy import (Column, Date, Integer, MetaData, Numeric, String,
                        Table, Text, create_engine, select)

from .domain import (Booking, BookingStatus, Listing, ListingStatus,
                     Review, User, UserRole)
from .repositories import InMemoryStore

metadata = MetaData()

users_t = Table("users", metadata,
    Column("id", Integer, primary_key=True), Column("email", String, unique=True),
    Column("password_hash", String), Column("full_name", String), Column("role", String))

listings_t = Table("listings", metadata,
    Column("id", Integer, primary_key=True), Column("host_id", Integer),
    Column("title", String), Column("description", Text), Column("address", String),
    Column("city", String), Column("state", String), Column("zip", String),
    Column("lat", Numeric), Column("lng", Numeric), Column("price_per_night", Numeric),
    Column("max_guests", Integer), Column("bedrooms", Integer), Column("bathrooms", Integer),
    Column("amenities", Text), Column("available_times", String), Column("status", String),
    Column("photos", Text), Column("videos", Text))

bookings_t = Table("bookings", metadata,
    Column("id", Integer, primary_key=True), Column("listing_id", Integer),
    Column("customer_id", Integer), Column("check_in", Date), Column("check_out", Date),
    Column("guests", Integer), Column("total_price", Numeric), Column("status", String),
    Column("booked_date", Date))

reviews_t = Table("reviews", metadata,
    Column("id", Integer, primary_key=True), Column("booking_id", Integer),
    Column("listing_id", Integer), Column("customer_id", Integer),
    Column("rating", Integer), Column("comment", Text))


def get_db_url():
    return os.environ.get("STAYNEST_DB_URL", "")


def _row_to_user(r):
    return User(id=r.id, email=r.email, password_hash=r.password_hash, full_name=r.full_name, role=UserRole(r.role))

def _row_to_listing(r):
    return Listing(id=r.id, host_id=r.host_id, title=r.title, description=r.description,
        address=r.address, city=r.city, state=r.state, zip=r.zip, lat=float(r.lat), lng=float(r.lng),
        price_per_night=Decimal(str(r.price_per_night)), max_guests=r.max_guests, bedrooms=r.bedrooms,
        bathrooms=r.bathrooms, amenities=json.loads(r.amenities or "[]"),
        available_times=r.available_times, status=ListingStatus(r.status),
        photos=json.loads(r.photos or "[]"), videos=json.loads(getattr(r, "videos", None) or "[]"))

def _row_to_booking(r):
    return Booking(id=r.id, listing_id=r.listing_id, customer_id=r.customer_id, check_in=r.check_in,
        check_out=r.check_out, guests=r.guests, total_price=Decimal(str(r.total_price)),
        status=BookingStatus(r.status), booked_date=r.booked_date)

def _row_to_review(r):
    return Review(id=r.id, booking_id=r.booking_id, listing_id=r.listing_id, customer_id=r.customer_id,
        rating=r.rating, comment=r.comment or "")


def _upsert(conn, table, values):
    pk = values["id"]
    existing = conn.execute(select(table.c.id).where(table.c.id == pk)).first()
    if existing:
        conn.execute(table.update().where(table.c.id == pk).values(**values))
    else:
        conn.execute(table.insert().values(**values))


class SqlBackedStore(InMemoryStore):
    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        with engine.begin() as conn:
            metadata.create_all(conn)
            self.users = [_row_to_user(r) for r in conn.execute(select(users_t)).all()]
            self.listings = [_row_to_listing(r) for r in conn.execute(select(listings_t)).all()]
            self.bookings = [_row_to_booking(r) for r in conn.execute(select(bookings_t)).all()]
            self.reviews = [_row_to_review(r) for r in conn.execute(select(reviews_t)).all()]

    def save(self, obj):
        super().save(obj)
        self.persist(obj)
        return obj

    def persist(self, obj):
        with self._engine.begin() as conn:
            if isinstance(obj, User):
                _upsert(conn, users_t, dict(id=obj.id, email=obj.email, password_hash=obj.password_hash,
                    full_name=obj.full_name, role=obj.role.value))
            elif isinstance(obj, Listing):
                _upsert(conn, listings_t, dict(id=obj.id, host_id=obj.host_id, title=obj.title,
                    description=obj.description, address=obj.address, city=obj.city, state=obj.state,
                    zip=obj.zip, lat=obj.lat, lng=obj.lng, price_per_night=Decimal(str(obj.price_per_night)),
                    max_guests=obj.max_guests, bedrooms=obj.bedrooms, bathrooms=obj.bathrooms,
                    amenities=json.dumps(obj.amenities), available_times=obj.available_times,
                    status=obj.status.value, photos=json.dumps(getattr(obj, "photos", [])), videos=json.dumps(getattr(obj, "videos", []))))
            elif isinstance(obj, Booking):
                _upsert(conn, bookings_t, dict(id=obj.id, listing_id=obj.listing_id, customer_id=obj.customer_id,
                    check_in=obj.check_in, check_out=obj.check_out, guests=obj.guests,
                    total_price=Decimal(str(obj.total_price)), status=obj.status.value, booked_date=obj.booked_date))
            elif isinstance(obj, Review):
                _upsert(conn, reviews_t, dict(id=obj.id, booking_id=obj.booking_id, listing_id=obj.listing_id,
                    customer_id=obj.customer_id, rating=obj.rating, comment=obj.comment))

    def flush(self):
        for coll in (self.users, self.listings, self.bookings, self.reviews):
            for obj in coll:
                self.persist(obj)


def make_store():
    """Return a SqlBackedStore if STAYNEST_DB_URL is set, else None (caller uses InMemoryStore)."""
    url = get_db_url()
    if not url:
        return None
    engine = create_engine(url, future=True)
    return SqlBackedStore(engine)


def flush_store(store):
    """Persist in-place mutations (approve/cancel/complete/edit/remove) if this is a SQL store."""
    flush = getattr(store, "flush", None)
    if callable(flush):
        flush()
