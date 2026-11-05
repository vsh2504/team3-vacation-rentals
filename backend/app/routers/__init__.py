"""Pattern: Composite - the API is one tree of routers mounted as a unit."""
from . import admin, analytics, auth, bookings, listings, reviews, uploads

ROUTERS = (auth.router, admin.router, listings.router, bookings.router,
           reviews.router, analytics.router, uploads.router)


def include_all(app) -> None:
    for router in ROUTERS:
        app.include_router(router)
