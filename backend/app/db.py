"""Sprint 3 — Database persistence (opt-in, write-through).

Default dev mode is still the in-memory store (see routers/common.py),
so `uvicorn app.main:app` works with zero setup and all Week 1 tests
pass without a database.

Set STAYNEST_DB_URL to use a real database, e.g.:
  STAYNEST_DB_URL=sqlite:///./staynest.db
  STAYNEST_DB_URL=postgresql+psycopg://staynest:staynest@localhost:5432/staynest

How it works: SqlBackedStore is an InMemoryStore that, on startup,
loads its lists from the DB, and on every save() inserts that row in
the DB. Mutations that happen in place (approve, cancel, complete,
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

from sqlalchemy import (CheckConstraint, Column, Date, DateTime, ForeignKey,
                        Index, Integer, MetaData, Numeric, String, Table, Text,
                        Time, UniqueConstraint, create_engine, func, select, text)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.exc import IntegrityError

from .core.errors import ApiError
from .domain import (Booking, BookingStatus, Listing, ListingStatus,
                     Review, User, UserRole)
from .repositories import InMemoryStore

metadata = MetaData()

users_t = Table("users", metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(320), nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    Column("full_name", String, nullable=False),
    Column("role", String(16), nullable=False),
    Column("phone", String(40)),
    CheckConstraint("role IN ('CUSTOMER', 'HOST', 'ADMIN')", name="ck_users_role"))

listings_t = Table("listings", metadata,
    Column("id", Integer, primary_key=True),
    Column("host_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("title", String, nullable=False), Column("description", Text, nullable=False),
    Column("address", String, nullable=False), Column("city", String, nullable=False),
    Column("state", String(2), nullable=False), Column("zip", String(10), nullable=False),
    Column("lat", Numeric(9, 6), nullable=False), Column("lng", Numeric(10, 6), nullable=False),
    Column("price_per_night", Numeric(12, 2), nullable=False),
    Column("max_guests", Integer, nullable=False),
    Column("bedrooms", Integer, nullable=False), Column("bathrooms", Integer, nullable=False),
    Column("host_contact_name", String, nullable=False, server_default=""),
    Column("host_contact_email", String(320), nullable=False, server_default=""),
    Column("host_contact_phone", String(40), nullable=False, server_default=""),
    Column("operating_start_time", Time, nullable=False, server_default=text("'00:00:00'")),
    Column("operating_end_time", Time, nullable=False, server_default=text("'23:59:00'")),
    Column("check_in_time", Time, nullable=False, server_default=text("'15:00:00'")),
    Column("check_out_time", Time, nullable=False, server_default=text("'11:00:00'")),
    Column("amenities", Text, nullable=False, server_default="[]"),
    Column("available_times", String, nullable=False),
    Column("status", String(24), nullable=False),
    Column("photos", Text, nullable=False, server_default="[]"),
    Column("videos", Text, nullable=False, server_default="[]"),
    CheckConstraint("price_per_night > 0", name="ck_listings_positive_price"),
    CheckConstraint("max_guests > 0", name="ck_listings_positive_capacity"),
    CheckConstraint("bedrooms >= 0 AND bathrooms >= 0", name="ck_listings_nonnegative_rooms"),
    CheckConstraint("lat BETWEEN -90 AND 90", name="ck_listings_latitude"),
    CheckConstraint("lng BETWEEN -180 AND 180", name="ck_listings_longitude"),
    CheckConstraint("operating_start_time <> operating_end_time", name="ck_listings_operating_window"),
    CheckConstraint("status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'REMOVED')",
                    name="ck_listings_status"))

bookings_t = Table("bookings", metadata,
    Column("id", Integer, primary_key=True),
    Column("listing_id", Integer, ForeignKey("listings.id", ondelete="RESTRICT"), nullable=False),
    Column("customer_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("check_in", Date, nullable=False), Column("check_out", Date, nullable=False),
    Column("check_in_time", Time, nullable=False, server_default=text("'15:00:00'")),
    Column("check_out_time", Time, nullable=False, server_default=text("'11:00:00'")),
    Column("guests", Integer, nullable=False),
    Column("total_price", Numeric(12, 2), nullable=False),
    Column("status", String(16), nullable=False), Column("booked_date", Date, nullable=False),
    Column("cancelled_at", DateTime(timezone=True)),
    Column("location_name", String, nullable=False, server_default=""),
    Column("location_address", String, nullable=False, server_default=""),
    Column("location_city", String, nullable=False, server_default=""),
    Column("location_state", String(2), nullable=False, server_default=""),
    Column("location_zip", String(10), nullable=False, server_default=""),
    Column("location_lat", Numeric(9, 6)), Column("location_lng", Numeric(10, 6)),
    CheckConstraint("check_out > check_in", name="ck_bookings_positive_stay"),
    CheckConstraint("check_out <= check_in + 14", name="ck_bookings_max_14_nights")
        .ddl_if(dialect="postgresql"),
    CheckConstraint("julianday(check_out) - julianday(check_in) <= 14",
                    name="ck_bookings_max_14_nights_sqlite").ddl_if(dialect="sqlite"),
    CheckConstraint("guests > 0", name="ck_bookings_positive_guests"),
    CheckConstraint("total_price >= 0", name="ck_bookings_nonnegative_total"),
    CheckConstraint("status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')", name="ck_bookings_status"))

ExcludeConstraint(
    (bookings_t.c.listing_id, "="),
    (func.tsrange(bookings_t.c.check_in + bookings_t.c.check_in_time,
                  bookings_t.c.check_out + bookings_t.c.check_out_time, "[)"), "&&"),
    where=text("status = 'CONFIRMED'"), using="gist",
    name="excl_bookings_confirmed_overlap",
).ddl_if(dialect="postgresql")

reviews_t = Table("reviews", metadata,
    Column("id", Integer, primary_key=True),
    Column("booking_id", Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
    Column("listing_id", Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
    Column("customer_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("rating", Integer, nullable=False),
    Column("comment", Text, nullable=False, server_default=""),
    UniqueConstraint("booking_id", name="uq_reviews_booking"),
    CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"))

Index("idx_listings_host_status", listings_t.c.host_id, listings_t.c.status)
Index("idx_listings_location_status", listings_t.c.city, listings_t.c.state,
      listings_t.c.zip, listings_t.c.status)
Index("idx_bookings_listing_status", bookings_t.c.listing_id, bookings_t.c.status)
Index("idx_bookings_customer_status", bookings_t.c.customer_id, bookings_t.c.status)
Index("idx_reviews_listing", reviews_t.c.listing_id)


def get_db_url():
    return os.environ.get("STAYNEST_DB_URL", "")


def _row_to_user(r):
    return User(id=r.id, email=r.email, password_hash=r.password_hash, full_name=r.full_name,
                role=UserRole(r.role), phone=r.phone)

def _row_to_listing(r):
    return Listing(id=r.id, host_id=r.host_id, title=r.title, description=r.description,
        address=r.address, city=r.city, state=r.state, zip=r.zip, lat=float(r.lat), lng=float(r.lng),
        price_per_night=Decimal(str(r.price_per_night)), max_guests=r.max_guests, bedrooms=r.bedrooms,
        bathrooms=r.bathrooms, host_contact_name=r.host_contact_name,
        host_contact_email=r.host_contact_email, host_contact_phone=r.host_contact_phone,
        operating_start_time=r.operating_start_time, operating_end_time=r.operating_end_time,
        check_in_time=r.check_in_time, check_out_time=r.check_out_time,
        amenities=json.loads(r.amenities or "[]"),
        available_times=r.available_times, status=ListingStatus(r.status),
        photos=json.loads(r.photos or "[]"), videos=json.loads(getattr(r, "videos", None) or "[]"))

def _row_to_booking(r):
    return Booking(id=r.id, listing_id=r.listing_id, customer_id=r.customer_id, check_in=r.check_in,
        check_out=r.check_out, guests=r.guests, total_price=Decimal(str(r.total_price)),
        status=BookingStatus(r.status), check_in_time=r.check_in_time,
        check_out_time=r.check_out_time, location_name=r.location_name,
        location_address=r.location_address, location_city=r.location_city,
        location_state=r.location_state, location_zip=r.location_zip,
        location_lat=float(r.location_lat) if r.location_lat is not None else None,
        location_lng=float(r.location_lng) if r.location_lng is not None else None,
        booked_date=r.booked_date, cancelled_at=r.cancelled_at)

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

def _write(conn, table, values, *, insert_only: bool):
    if insert_only:
        conn.execute(table.insert().values(**values))
    else:
        _upsert(conn, table, values)

def _constraint_name(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)


class SqlBackedStore(InMemoryStore):
    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            metadata.create_all(conn)
            self.users = [_row_to_user(r) for r in conn.execute(select(users_t)).all()]
            self.listings = [_row_to_listing(r) for r in conn.execute(select(listings_t)).all()]
            self.bookings = [_row_to_booking(r) for r in conn.execute(select(bookings_t)).all()]
            self.reviews = [_row_to_review(r) for r in conn.execute(select(reviews_t)).all()]
        self._seed_empty_database()

    def _seed_empty_database(self):
        """Seed a brand-new development database once, with stable IDs."""
        if self.users or self.listings or self.bookings or self.reviews:
            return
        from .core.security import hash_password
        from .seed import load_seed

        seed_users = [
            User(id=host_id, email=f"host{host_id}@staynest.local",
                 password_hash=hash_password("password123"), full_name=f"Demo Host {host_id}",
                 role=UserRole.HOST, phone=f"408-555-01{host_id:02d}")
            for host_id in range(1, 5)
        ]
        seed_users.append(User(id=99, email="admin@staynest.local",
                               password_hash=hash_password("admin12345"),
                               full_name="Demo Admin", role=UserRole.ADMIN))
        seeded_store = InMemoryStore()
        load_seed(seeded_store)
        hosts = {user.id: user for user in seed_users}
        for listing in seeded_store.listings:
            host = hosts[listing.host_id]
            listing.host_contact_name = host.full_name
            listing.host_contact_email = host.email
            listing.host_contact_phone = host.phone or ""

        # One transaction makes first-run seeding retry-safe after an interruption.
        with self._engine.begin() as conn:
            for user in seed_users:
                conn.execute(users_t.insert().values(
                    id=user.id, email=user.email, password_hash=user.password_hash,
                    full_name=user.full_name, role=user.role.value, phone=user.phone))
            for listing in seeded_store.listings:
                conn.execute(listings_t.insert().values(
                    id=listing.id, host_id=listing.host_id, title=listing.title,
                    description=listing.description, address=listing.address,
                    city=listing.city, state=listing.state, zip=listing.zip,
                    lat=listing.lat, lng=listing.lng,
                    price_per_night=Decimal(str(listing.price_per_night)),
                    max_guests=listing.max_guests, bedrooms=listing.bedrooms,
                    bathrooms=listing.bathrooms,
                    host_contact_name=listing.host_contact_name,
                    host_contact_email=listing.host_contact_email,
                    host_contact_phone=listing.host_contact_phone,
                    operating_start_time=listing.operating_start_time,
                    operating_end_time=listing.operating_end_time,
                    check_in_time=listing.check_in_time,
                    check_out_time=listing.check_out_time,
                    amenities=json.dumps(listing.amenities),
                    available_times=listing.available_times,
                    status=listing.status.value, photos=json.dumps(listing.photos),
                    videos=json.dumps(listing.videos)))
        self.users = seed_users
        self.listings = seeded_store.listings

    def save(self, obj):
        self.persist(obj, insert_only=True)
        return super().save(obj)

    def persist(self, obj, *, insert_only=False):
        try:
            self._persist(obj, insert_only=insert_only)
        except IntegrityError as exc:
            constraint = _constraint_name(exc)
            detail = str(exc.orig)
            if isinstance(obj, Booking) and (
                    constraint in {"excl_bookings_confirmed_overlap", "bookings_pkey"}
                    or "UNIQUE constraint failed: bookings.id" in detail):
                raise ApiError("CONFLICT", "Listing is not available for the requested dates and times") from exc
            if isinstance(obj, Review) and (
                    constraint == "uq_reviews_booking"
                    or "UNIQUE constraint failed: reviews.booking_id" in detail):
                raise ApiError("CONFLICT", "One review per booking") from exc
            raise

    def _persist(self, obj, *, insert_only=False):
        with self._engine.begin() as conn:
            if isinstance(obj, User):
                _write(conn, users_t, dict(id=obj.id, email=obj.email, password_hash=obj.password_hash,
                    full_name=obj.full_name, role=obj.role.value, phone=obj.phone),
                    insert_only=insert_only)
            elif isinstance(obj, Listing):
                _write(conn, listings_t, dict(id=obj.id, host_id=obj.host_id, title=obj.title,
                    description=obj.description, address=obj.address, city=obj.city, state=obj.state,
                    zip=obj.zip, lat=obj.lat, lng=obj.lng, price_per_night=Decimal(str(obj.price_per_night)),
                    max_guests=obj.max_guests, bedrooms=obj.bedrooms, bathrooms=obj.bathrooms,
                    host_contact_name=obj.host_contact_name, host_contact_email=obj.host_contact_email,
                    host_contact_phone=obj.host_contact_phone,
                    operating_start_time=obj.operating_start_time,
                    operating_end_time=obj.operating_end_time,
                    check_in_time=obj.check_in_time, check_out_time=obj.check_out_time,
                    amenities=json.dumps(obj.amenities), available_times=obj.available_times,
                    status=obj.status.value, photos=json.dumps(getattr(obj, "photos", [])),
                    videos=json.dumps(getattr(obj, "videos", []))), insert_only=insert_only)
            elif isinstance(obj, Booking):
                listing = next((row for row in self.listings if row.id == obj.listing_id), None)
                if listing and not obj.location_address:
                    obj.location_name = listing.title
                    obj.location_address = listing.address
                    obj.location_city = listing.city
                    obj.location_state = listing.state
                    obj.location_zip = listing.zip
                    obj.location_lat = listing.lat
                    obj.location_lng = listing.lng
                _write(conn, bookings_t, dict(id=obj.id, listing_id=obj.listing_id,
                    customer_id=obj.customer_id, check_in=obj.check_in, check_out=obj.check_out,
                    check_in_time=obj.check_in_time, check_out_time=obj.check_out_time,
                    guests=obj.guests, total_price=Decimal(str(obj.total_price)),
                    status=obj.status.value, booked_date=obj.booked_date,
                    cancelled_at=obj.cancelled_at, location_name=obj.location_name,
                    location_address=obj.location_address, location_city=obj.location_city,
                    location_state=obj.location_state, location_zip=obj.location_zip,
                    location_lat=obj.location_lat, location_lng=obj.location_lng),
                    insert_only=insert_only)
            elif isinstance(obj, Review):
                _write(conn, reviews_t, dict(id=obj.id, booking_id=obj.booking_id,
                    listing_id=obj.listing_id, customer_id=obj.customer_id,
                    rating=obj.rating, comment=obj.comment), insert_only=insert_only)

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
