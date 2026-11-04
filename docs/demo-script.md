# Demo script — 4 moments, in order (Sprint 4)

Setup (fresh server, so data is known): `uvicorn app.main:app --port 8000`
in one terminal, `npm run dev` in frontend/ in another. Open
http://localhost:5173 and http://localhost:8000/docs in two tabs.

## Moment 1 — Find a Stay (Vinayak, ~2 min)
Search San Jose, 4 guests, 3 nights -> map + list -> open a listing.
Show photos, amenities, cost, rating, reviews, # booked today.

## Moment 2 — Book & Cancel (Manoj, ~2 min)
Log in as a Customer, book the listing -> confirmation with total.
Try the same dates again -> blocked (409). Cancel -> dates free again
(book again to prove it).

## Moment 3 — Identity & Admin (Ranadhir, ~2 min)
Log in as Host, create a listing -> it does NOT appear in search.
Log in as Admin (admin@staynest.local / admin12345, demo only),
approve it in the Admin queue -> it appears in search.
Log in as each role and show the nav change.

## Moment 4 — Trust & Analytics (Prajval, ~2 min)
Book past dates, mark completed, submit a review -> rating updates
on the listing. Open Analytics as Host (own listings, 30/60/90, zip)
and as Admin (platform totals).

## Rehearsal note
Rehearse twice before Demo Day (Sprint 4 acceptance). If the API is
down, search falls back to seed data — say so out loud; do not pretend
the fallback is the API.
