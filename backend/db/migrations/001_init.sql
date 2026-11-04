-- Sprint 3, US31 — initial schema. Matches backend/app/db.py exactly.
-- Apply: psql "$DATABASE_URL" -f backend/db/migrations/001_init.sql
-- Rollback: DROP TABLE reviews, bookings, listings, users;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL, full_name TEXT NOT NULL, role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS listings (
  id INTEGER PRIMARY KEY, host_id INTEGER NOT NULL, title TEXT NOT NULL,
  description TEXT NOT NULL, address TEXT NOT NULL, city TEXT NOT NULL,
  state TEXT NOT NULL, zip TEXT NOT NULL, lat NUMERIC NOT NULL, lng NUMERIC NOT NULL,
  price_per_night NUMERIC NOT NULL, max_guests INTEGER NOT NULL,
  bedrooms INTEGER NOT NULL, bathrooms INTEGER NOT NULL,
  amenities TEXT NOT NULL DEFAULT '[]', available_times TEXT NOT NULL,
  status TEXT NOT NULL, photos TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL, customer_id INTEGER NOT NULL,
  check_in DATE NOT NULL, check_out DATE NOT NULL, guests INTEGER NOT NULL,
  total_price NUMERIC NOT NULL, status TEXT NOT NULL, booked_date DATE
);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL, listing_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL, rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_listings_zip_status ON listings(zip, status);
CREATE INDEX IF NOT EXISTS idx_bookings_listing ON bookings(listing_id, status);
