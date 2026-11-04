# Wireframes — 18 screens (Week 1 inventory)

Drawn as descriptions + ASCII layouts in Week 1; Figma/Pencil exports
replace the ASCII in Sprint 1 without changing screen order or fields.
Each screen notes its primary action, error state, and empty state.

## Customer (8)
1. Landing/Search — date, guests, duration, city/state/zip, address search.
   Error: 15-day stay -> "Stay cannot exceed 14 days" on check-out field.
   Empty: "No homes match — try fewer guests or different dates."
2. Search results list — photo, price, rating, # booked today, Book button.
3. Map view — pins = results, click pin -> listing detail.
4. Listing detail — gallery, amenities, cost breakdown, reviews, Book.
5. Booking form + confirmation — nights, total_price, Confirm.
6. My bookings — upcoming / past / cancelled tabs.
7. Cancel confirmation — "Cancel this stay? Dates become available again."
8. Review form — past bookings only, stars 1-5, comment. Error on upcoming: blocked.

## Host (5)
9. My listings — status badge PENDING/APPROVED/REJECTED/REMOVED.
10. Add listing form. 11. Edit listing (name/address/contact/hours/times/max guests/description/photos).
12. Listing detail (host view). 13. Host analytics — by zip, 30/60/90 toggle.

## Admin (3)
14. Pending approvals queue. 15. Moderation — approve / reject with reason / remove.
16. Platform analytics — by zip, 30/60/90 toggle.

## Shared (2)
17. Register (role CUSTOMER|HOST). 18. Login + role-based home (nav changes by role).

ASCII example — Search (screen 1):
```
+--------------------------------------------------+
| StayNest  [Customer|Host|Admin]    Login/Register |
+--------------------------------------------------+
| Where? [San Jose____]  Check-in [____] Check-out |
| Guests [2 v]  [Search]   [Map view]               |
| [Photo] Downtown Loft — $150/night — 4.8★        |
|         # booked today: 2   [Book]               |
+--------------------------------------------------+
```
