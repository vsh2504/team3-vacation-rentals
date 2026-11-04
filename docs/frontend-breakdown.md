# Frontend Breakdown — Everyone Gets a Named Frontend Piece (PR 12)

This mirrors docs/feature-breakdown.md § Core APIs, but for the web UI.
Every frontend file has an owner header at the top; the table below is
the map, not a substitute for reading the header. Cross-feature use is
explicit: a component owned by one agent can be rendered inside another
agent's page (BookingForm inside ListingDetail, ReviewForm inside
Bookings) — ownership follows the file, not the screen it happens to
appear on.

## Before / after — what "improved" means here

Week 1 frontend (PR 1-3) was a scaffold, honestly labelled as such:
- One page: SearchPage with seed data only, zip + guests filters.
- Role nav was three buttons that only changed a label; no login, no token.
- Book button did nothing; Edit button did nothing.
- Map was a placeholder list of lat/lng coordinates.
- No detail page, no host page, no bookings page, no admin page, no analytics.

Sprints 1-4 frontend (PR 11, split in PR 12) is the full app:
- Real routing (react-router-dom), real auth (token in localStorage,
  role nav that actually hides/shows links), API calls for every page,
  seed fallback only if the API is down (and it says so on screen).
- Search filters, detail with photos/rating/reviews/# booked today,
  booking with 409/422 messages from the API, cancel/complete/review,
  host CRUD, admin queue, analytics dashboards, map with pins.

## Split table

| Frontend piece | Owner | File(s) | Route / use | What it does |
|---|---|---|---|---|
| Search | Vinayak Gupta | frontend/src/pages/SearchPage.jsx | `/` | API search, city/state/zip/guests/dates, 14-day client check, results + map |
| Listing detail | Vinayak Gupta | frontend/src/pages/ListingDetailPage.jsx | `/listings/:id` | Photos, amenities, cost, rating, reviews, # booked today; renders Manoj's BookingForm |
| Listing card | Vinayak Gupta | frontend/src/components/ListingCard.jsx | used by Search | Card: photo, price, guests, amenities, # booked today |
| Map | Vinayak Gupta | frontend/src/components/MapView.jsx | used by Search | OSM embed (no key) / Google Maps embed (with key), pins = results, click pin -> detail |
| Host listings | Vinayak Gupta | frontend/src/pages/HostPage.jsx | `/host` | My listings, create/edit/delete; new listings start PENDING_APPROVAL |
| Auth + app shell | Ranadhir Reddy Rikkala | frontend/src/pages/AuthPage.jsx, frontend/src/App.jsx, frontend/src/main.jsx | `/auth`, nav | Register/login, token + user state, role nav, routing |
| Admin | Ranadhir Reddy Rikkala | frontend/src/pages/AdminPage.jsx | `/admin` | Pending queue approve/reject, all-listings remove |
| My bookings | Manoj | frontend/src/pages/BookingsPage.jsx | `/bookings` | Upcoming/past bookings, cancel, mark completed; renders Prajval's ReviewForm |
| Booking form | Manoj | frontend/src/components/BookingForm.jsx | used by ListingDetail | Check-in/out/guests, Book, shows API 409/422 verbatim |
| Analytics | Prajval Sudhir | frontend/src/pages/AnalyticsPage.jsx | `/analytics` | Host/admin dashboards, 30/60/90, zip filter, totals table |
| Review form | Prajval Sudhir | frontend/src/components/ReviewForm.jsx | used by Bookings | Rating 1-5 + comment for COMPLETED bookings only |
| API client | Shared, no single owner | frontend/src/api/client.js | all pages | Only place the frontend touches HTTP; every page imports from here |

Balance: Vinayak 5 files (largest bundle, team lead, demo opener),
Ranadhir 3, Manoj 2, Prajval 2, shared 1. Every agent has at least one
page AND one component or shell piece, and every agent's frontend piece
has a demo moment in docs/demo-script.md.

## Rules for frontend work (same as backend)
- No rule in React: validation messages come from the API; the UI only
  shows them. The one exception is the 14-day client check in Search,
  which is labelled as a hint — the API still returns 422.
- Role hiding in nav is UX, not security: the API enforces 403 on
  every protected endpoint, and the pages say so.
- No secrets in the frontend: Google Maps key comes from
  VITE_GOOGLE_MAPS_KEY at build time, never committed.
