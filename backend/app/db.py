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


# -- Data Mapper strategies: one per entity type ---------------------------------
class EntityMapper:
    """Translate one entity type to and from its table row (Strategy)."""

    table: Table

    def to_row(self, obj) -> dict:  # pragma: no cover - abstract
        raise NotImplementedError

    def from_row(self, row):  # pragma: no cover - abstract
        raise NotImplementedError


class UserMapper(EntityMapper):
    table = users_t

    def to_row(self, u):
        return dict(id=u.id, email=u.email, password_hash=u.password_hash,
                    full_name=u.full_name, role=u.role.value, phone=u.phone)

    def from_row(self, r):
        return User(id=r.id, email=r.email, password_hash=r.password_hash,
                    full_name=r.full_name, role=UserRole(r.role), phone=r.phone)


class ListingMapper(EntityMapper):
    table = listings_t

    def to_row(self, li):
        return dict(
            id=li.id, host_id=li.host_id, title=li.title, description=li.description,
            address=li.address, city=li.city, state=li.state, zip=li.zip,
            lat=li.lat, lng=li.lng, price_per_night=Decimal(str(li.price_per_night)),
            max_guests=li.max_guests, bedrooms=li.bedrooms, bathrooms=li.bathrooms,
            host_contact_name=li.host_contact_name, host_contact_email=li.host_contact_email,
            host_contact_phone=li.host_contact_phone,
            operating_start_time=li.operating_start_time,
            operating_end_time=li.operating_end_time,
            check_in_time=li.check_in_time, check_out_time=li.check_out_time,
            amenities=json.dumps(li.amenities), available_times=li.available_times,
            status=li.status.value, photos=json.dumps(li.photos),
            videos=json.dumps(li.videos))

    def from_row(self, r):
        return Listing(
            id=r.id, host_id=r.host_id, title=r.title, description=r.description,
            address=r.address, city=r.city, state=r.state, zip=r.zip,
            lat=float(r.lat), lng=float(r.lng),
            price_per_night=Decimal(str(r.price_per_night)), max_guests=r.max_guests,
            bedrooms=r.bedrooms, bathrooms=r.bathrooms,
            host_contact_name=r.host_contact_name, host_contact_email=r.host_contact_email,
            host_contact_phone=r.host_contact_phone,
            operating_start_time=r.operating_start_time, operating_end_time=r.operating_end_time,
            check_in_time=r.check_in_time, check_out_time=r.check_out_time,
            amenities=json.loads(r.amenities or "[]"), available_times=r.available_times,
            status=ListingStatus(r.status), photos=json.loads(r.photos or "[]"),
            videos=json.loads(getattr(r, "videos", None) or "[]"))


class BookingMapper(EntityMapper):
    table = bookings_t

    def to_row(self, b):
        return dict(
            id=b.id, listing_id=b.listing_id, customer_id=b.customer_id,
            check_in=b.check_in, check_out=b.check_out,
            check_in_time=b.check_in_time, check_out_time=b.check_out_time,
            guests=b.guests, total_price=Decimal(str(b.total_price)),
            status=b.status.value, booked_date=b.booked_date, cancelled_at=b.cancelled_at,
            location_name=b.location_name, location_address=b.location_address,
            location_city=b.location_city, location_state=b.location_state,
            location_zip=b.location_zip, location_lat=b.location_lat,
            location_lng=b.location_lng)

    def from_row(self, r):
        return Booking(
            id=r.id, listing_id=r.listing_id, customer_id=r.customer_id,
            check_in=r.check_in, check_out=r.check_out, guests=r.guests,
            total_price=Decimal(str(r.total_price)), status=BookingStatus(r.status),
            check_in_time=r.check_in_time, check_out_time=r.check_out_time,
            location_name=r.location_name, location_address=r.location_address,
            location_city=r.location_city, location_state=r.location_state,
            location_zip=r.location_zip,
            location_lat=float(r.location_lat) if r.location_lat is not None else None,
            location_lng=float(r.location_lng) if r.location_lng is not None else None,
            booked_date=r.booked_date, cancelled_at=r.cancelled_at)


class ReviewMapper(EntityMapper):
    table = reviews_t

    def to_row(self, rv):
        return dict(id=rv.id, booking_id=rv.booking_id, listing_id=rv.listing_id,
                    customer_id=rv.customer_id, rating=rv.rating, comment=rv.comment)

    def from_row(self, r):
        return Review(id=r.id, booking_id=r.booking_id, listing_id=r.listing_id,
                      customer_id=r.customer_id, rating=r.rating, comment=r.comment or "")


MAPPERS: dict[type, EntityMapper] = {
    User: UserMapper(), Listing: ListingMapper(),
    Booking: BookingMapper(), Review: ReviewMapper(),
}


def _write(conn, table, values, *, insert_only: bool):
    """Insert, or upsert by primary key unless ``insert_only``."""
    pk = values["id"]
    if not insert_only and conn.execute(select(table.c.id).where(table.c.id == pk)).first():
        conn.execute(table.update().where(table.c.id == pk).values(**values))
    else:
        conn.execute(table.insert().values(**values))


def _constraint_name(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)


def _enable_extensions(conn, dialect_name: str) -> None:
    """PostgreSQL needs btree_gist for the booking overlap exclusion constraint."""
    if dialect_name == "postgresql":
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))


def _is_booking_conflict(constraint, detail) -> bool:
    return (constraint in {"excl_bookings_confirmed_overlap", "bookings_pkey"}
            or "UNIQUE constraint failed: bookings.id" in detail)


def _is_duplicate_review(constraint, detail) -> bool:
    return (constraint == "uq_reviews_booking"
            or "UNIQUE constraint failed: reviews.booking_id" in detail)


class SqlBackedStore(InMemoryStore):
    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        with engine.begin() as conn:
            _enable_extensions(conn, engine.dialect.name)
            metadata.create_all(conn)
            load = lambda kind: [MAPPERS[kind].from_row(r)
                                 for r in conn.execute(select(MAPPERS[kind].table)).all()]
            self.users, self.listings = load(User), load(Listing)
            self.bookings, self.reviews = load(Booking), load(Review)
        self._seed_empty_database()
        from .demo_seed import seed_demo_reviews
        seed_demo_reviews(self)

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
            for entity in (*seed_users, *seeded_store.listings):
                mapper = MAPPERS[type(entity)]
                conn.execute(mapper.table.insert().values(**mapper.to_row(entity)))
        self.users = seed_users
        self.listings = seeded_store.listings

    def save(self, obj):
        self.persist(obj, insert_only=True)
        return super().save(obj)

    def persist(self, obj, *, insert_only=False):
        try:
            self._persist(obj, insert_only=insert_only)
        except IntegrityError as exc:
            constraint, detail = _constraint_name(exc), str(exc.orig)
            if isinstance(obj, Booking) and _is_booking_conflict(constraint, detail):
                raise ApiError("CONFLICT", "Listing is not available for the requested dates and times") from exc
            if isinstance(obj, Review) and _is_duplicate_review(constraint, detail):
                raise ApiError("CONFLICT", "One review per booking") from exc
            raise

    def _snapshot_booking_location(self, booking: Booking) -> None:
        """Capture the listing's location on a booking that has none yet."""
        listing = next((row for row in self.listings if row.id == booking.listing_id), None)
        if listing and not booking.location_address:
            booking.location_name = listing.title
            booking.location_address = listing.address
            booking.location_city = listing.city
            booking.location_state = listing.state
            booking.location_zip = listing.zip
            booking.location_lat = listing.lat
            booking.location_lng = listing.lng

    def _persist(self, obj, *, insert_only=False):
        mapper = MAPPERS.get(type(obj))
        if mapper is None:
            raise TypeError(f"Unsupported entity type: {type(obj).__name__}")
        if isinstance(obj, Booking):
            self._snapshot_booking_location(obj)
        with self._engine.begin() as conn:
            _write(conn, mapper.table, mapper.to_row(obj), insert_only=insert_only)

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
