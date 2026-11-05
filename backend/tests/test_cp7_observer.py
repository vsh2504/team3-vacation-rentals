"""CP7 - Observer: domain events published by services, consumed by subscribers."""
from datetime import date

import pytest

from app.core.errors import ApiError
from app.domain import (Booking, BookingStatus, Listing, ListingStatus, User, UserRole)
from app.events import (BookingCancelled, BookingCompleted, BookingConfirmed, Event,
                        EventBus, ListingModerated, NotificationLog, ReviewSubmitted,
                        EVENTS, NOTIFICATIONS)
from app.repositories import InMemoryStore
from app.services import BookingService, ListingService, ReviewService

D = date(2027, 5, 1)


def test_subscribers_receive_matching_events_only():
    bus, seen = EventBus(), []
    bus.subscribe(BookingConfirmed, seen.append)
    bus.publish(BookingConfirmed(1, 2, 3, 4))
    bus.publish(BookingCancelled(1, 2, 3, 4))
    assert [type(e) for e in seen] == [BookingConfirmed]


def test_base_event_subscription_sees_everything_and_unsubscribe_stops_it():
    bus, seen = EventBus(), []
    unsubscribe = bus.subscribe(Event, seen.append)
    bus.publish(BookingCancelled(1, 2, 3, 4))
    unsubscribe()
    bus.publish(BookingCancelled(1, 2, 3, 4))
    assert len(seen) == 1


def test_failing_subscriber_does_not_break_publisher_or_other_subscribers():
    bus, seen = EventBus(), []

    def boom(_event):
        raise RuntimeError("subscriber bug")

    bus.subscribe(Event, boom)
    bus.subscribe(Event, seen.append)
    bus.publish(BookingCancelled(1, 2, 3, 4))
    assert len(seen) == 1 and len(bus.errors) == 1


def test_notification_log_formats_each_event_for_the_host():
    log = NotificationLog()
    for event in (BookingConfirmed(1, 2, 3, 9), BookingCancelled(1, 2, 3, 9),
                  BookingCompleted(1, 2, 3, 9), ReviewSubmitted(1, 2, 3, 9, 5),
                  ListingModerated(2, 9, "APPROVED")):
        log.on_event(event)
    assert [n.kind for n in log.items] == [
        "booking.confirmed", "booking.cancelled", "booking.completed",
        "review.submitted", "listing.moderated"]
    assert all(n.recipient_id == 9 and n.message for n in log.items)


def test_events_without_a_recipient_are_not_logged():
    log = NotificationLog()
    log.on_event(BookingConfirmed(1, 2, 3, None))
    assert log.items == []


def test_default_bus_feeds_the_global_notification_log():
    before = len(NOTIFICATIONS.items)
    EVENTS.publish(BookingCancelled(1, 2, 3, 77))
    assert len(NOTIFICATIONS.items) == before + 1


# ---- services publish events ------------------------------------------------
def _world():
    store, bus = InMemoryStore(), EventBus()
    host = User(1, "h@x.io", "x", "Host", UserRole.HOST)
    cust = User(2, "c@x.io", "x", "Cust", UserRole.CUSTOMER)
    admin = User(3, "a@x.io", "x", "Admin", UserRole.ADMIN)
    store.users += [host, cust, admin]
    store.listings.append(Listing(
        id=1, host_id=1, title="T", description="d", address="a", city="c", state="s",
        zip="95110", lat=1.0, lng=1.0, price_per_night=100, max_guests=2, bedrooms=1,
        bathrooms=1, status=ListingStatus.APPROVED))
    seen = []
    bus.subscribe(Event, seen.append)
    return store, bus, seen, host, cust, admin


def test_booking_lifecycle_publishes_events():
    store, bus, seen, host, cust, _ = _world()
    service = BookingService(store, events=bus)
    booking = service.book(cust, 1, date(2027, 5, 1), date(2027, 5, 3), 2, today=D)
    service.cancel(cust, booking.id)
    past = service.book(cust, 1, date(2026, 1, 1), date(2026, 1, 3), 2, today=D)
    service.complete(cust, past.id, today=D)
    assert [type(e) for e in seen] == [BookingConfirmed, BookingCancelled,
                                       BookingConfirmed, BookingCompleted]
    assert seen[0].host_id == 1 and seen[0].customer_id == 2


def test_failed_booking_publishes_nothing():
    store, bus, seen, host, cust, _ = _world()
    with pytest.raises(ApiError):
        BookingService(store, events=bus).book(host, 1, date(2027, 5, 1), date(2027, 5, 3), 2, today=D)
    assert seen == []


def test_review_and_moderation_publish_events():
    store, bus, seen, host, cust, admin = _world()
    store.bookings.append(Booking(
        id=1, listing_id=1, customer_id=2, check_in=date(2026, 1, 1),
        check_out=date(2026, 1, 3), guests=2, total_price=200,
        status=BookingStatus.COMPLETED, booked_date=D))
    ReviewService(store, events=bus).submit(cust, 1, 5, "great", today=D)
    ListingService(store, events=bus).approve(admin, 1, False)
    assert [type(e) for e in seen] == [ReviewSubmitted, ListingModerated]
    assert seen[1].status == "REJECTED"


def test_plain_event_defaults():
    assert Event().message == "event" and Event().recipient_id is None
