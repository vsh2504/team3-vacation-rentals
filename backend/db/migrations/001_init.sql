-- StayNest PostgreSQL baseline schema.
-- Apply: psql "$STAYNEST_DB_URL" -f backend/db/migrations/001_init.sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email VARCHAR(320) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role VARCHAR(16) NOT NULL CONSTRAINT ck_users_role
    CHECK (role IN ('CUSTOMER', 'HOST', 'ADMIN')),
  phone VARCHAR(40)
);

CREATE TABLE IF NOT EXISTS listings (
  id INTEGER PRIMARY KEY,
  host_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  state VARCHAR(2) NOT NULL,
  zip VARCHAR(10) NOT NULL,
  lat NUMERIC(9, 6) NOT NULL CONSTRAINT ck_listings_latitude CHECK (lat BETWEEN -90 AND 90),
  lng NUMERIC(10, 6) NOT NULL CONSTRAINT ck_listings_longitude CHECK (lng BETWEEN -180 AND 180),
  price_per_night NUMERIC(12, 2) NOT NULL CONSTRAINT ck_listings_positive_price CHECK (price_per_night > 0),
  max_guests INTEGER NOT NULL CONSTRAINT ck_listings_positive_capacity CHECK (max_guests > 0),
  bedrooms INTEGER NOT NULL,
  bathrooms INTEGER NOT NULL,
  host_contact_name TEXT NOT NULL DEFAULT '',
  host_contact_email VARCHAR(320) NOT NULL DEFAULT '',
  host_contact_phone VARCHAR(40) NOT NULL DEFAULT '',
  operating_start_time TIME NOT NULL DEFAULT TIME '00:00:00',
  operating_end_time TIME NOT NULL DEFAULT TIME '23:59:00',
  check_in_time TIME NOT NULL DEFAULT TIME '15:00:00',
  check_out_time TIME NOT NULL DEFAULT TIME '11:00:00',
  amenities TEXT NOT NULL DEFAULT '[]',
  available_times TEXT NOT NULL,
  status VARCHAR(24) NOT NULL,
  photos TEXT NOT NULL DEFAULT '[]',
  videos TEXT NOT NULL DEFAULT '[]',
  CONSTRAINT ck_listings_nonnegative_rooms CHECK (bedrooms >= 0 AND bathrooms >= 0),
  CONSTRAINT ck_listings_operating_window CHECK (operating_start_time <> operating_end_time),
  CONSTRAINT ck_listings_status CHECK (
    status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'REMOVED')
  )
);

CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY,
  listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE RESTRICT,
  customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  check_in_time TIME NOT NULL DEFAULT TIME '15:00:00',
  check_out_time TIME NOT NULL DEFAULT TIME '11:00:00',
  guests INTEGER NOT NULL CONSTRAINT ck_bookings_positive_guests CHECK (guests > 0),
  total_price NUMERIC(12, 2) NOT NULL CONSTRAINT ck_bookings_nonnegative_total CHECK (total_price >= 0),
  status VARCHAR(16) NOT NULL CONSTRAINT ck_bookings_status
    CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
  booked_date DATE NOT NULL,
  cancelled_at TIMESTAMPTZ,
  location_name TEXT NOT NULL DEFAULT '',
  location_address TEXT NOT NULL DEFAULT '',
  location_city TEXT NOT NULL DEFAULT '',
  location_state VARCHAR(2) NOT NULL DEFAULT '',
  location_zip VARCHAR(10) NOT NULL DEFAULT '',
  location_lat NUMERIC(9, 6),
  location_lng NUMERIC(10, 6),
  CONSTRAINT ck_bookings_positive_stay CHECK (check_out > check_in),
  CONSTRAINT ck_bookings_max_14_nights CHECK (check_out <= check_in + 14),
  CONSTRAINT excl_bookings_confirmed_overlap EXCLUDE USING gist (
    listing_id WITH =,
    tsrange(check_in + check_in_time, check_out + check_out_time, '[)') WITH &&
  ) WHERE (status = 'CONFIRMED')
);

CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY,
  booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL CONSTRAINT ck_reviews_rating CHECK (rating BETWEEN 1 AND 5),
  comment TEXT NOT NULL DEFAULT '',
  CONSTRAINT uq_reviews_booking UNIQUE (booking_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_host_status ON listings(host_id, status);
CREATE INDEX IF NOT EXISTS idx_listings_location_status ON listings(city, state, zip, status);
CREATE INDEX IF NOT EXISTS idx_bookings_listing_status ON bookings(listing_id, status);
CREATE INDEX IF NOT EXISTS idx_bookings_customer_status ON bookings(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_reviews_listing ON reviews(listing_id);
