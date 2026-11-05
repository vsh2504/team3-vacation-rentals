"""CP10 - Memento (undo listing edits) and Mediator (booking coordination)."""
from datetime import date

import pytest

from app.core.errors import ApiError
from app.domain import Listing, ListingStatus, User, UserRole
from app.events import BookingConfirmed, Event, EventBus
from app.listing_history import ListingHistory, ListingMemento
from app.price_quotes import DEFAULT_QUOTE, FlatFee
from app.repositories import InMemoryStore
from app.services import BookingService, ListingService
from app.services.booking_mediator import BookingMediator

D = date(2027, 5, 1)


def make_listing(**kw):
    base = dict(id=1, host_id=1, title="Old", description="d", address="1 Main", city="San Jose",
                state="CA", zip="95110", lat=37.3, lng=-121.9, price_per_night=100,
                max_guests=2, bedrooms=1, bathrooms=1, amenities=["wifi"],
                status=ListingStatus.APPROVED)
    base.update(kw)
    return Listing(**base)


# ---- Memento ---------------------------------------------------------------------
def test_memento_is_a_deep_snapshot():
    listing = make_listing()
    memento = ListingMemento.capture(listing)
    listing.title = "New"
    listing.amenities.append("pool")
    memento.restore(listing)
    assert listing.title == "Old" and listing.amenities == ["wifi"]


def test_restoring_twice_does_not_alias_the_snapshot():
    listing = make_listing()
    memento = ListingMemento.capture(listing)
    memento.restore(listing)
    listing.amenities.append("pool")
    memento.restore(listing)
    assert listing.amenities == ["wifi"]


def test_history_is_a_per_listing_stack_with_a_limit():
    history, listing = ListingHistory(limit=2), make_listing()
    for title in ("v1", "v2", "v3"):
        listing.title = title
        history.save(listing)
    other = make_listing(id=2, title="other")
    history.save(other)
    assert history.depth(1) == 2 and history.depth(2) == 1
    assert history.undo(listing) is True and listing.title == "v3"
    assert history.undo(listing) is True and listing.title == "v2"
    assert history.undo(listing) is False and history.depth(1) == 0


def test_service_edit_can_be_undone_by_the_owner():
    store, history = InMemoryStore(), ListingHistory()
    host = User(1, "h@x.io", "x", "Host", UserRole.HOST)
    store.users.append(host)
    store.listings.append(make_listing())
    service = ListingService(store, history=history, events=EventBus())
    service.update(host, 1, {"title": "Edited", "description": "d", "address": "1 Main",
                             "city": "San Jose", "state": "CA", "zip": "95110", "lat": 37.3,
                             "lng": -121.9, "price_per_night": 100, "max_guests": 2,
                             "bedrooms": 1, "bathrooms": 1})
    listing = store.listings[0]
    assert listing.title == "Edited" and listing.status == ListingStatus.PENDING_APPROVAL
    assert service.undo_last_edit(host, 1).title == "Old"
    assert listing.status == ListingStatus.APPROVED
    with pytest.raises(ApiError) as nothing:
        service.undo_last_edit(host, 1)
    assert nothing.value.code == "CONFLICT"


def test_only_the_owner_can_undo():
    store = InMemoryStore()
    store.listings.append(make_listing())
    stranger = User(2, "s@x.io", "x", "S", UserRole.HOST)
    with pytest.raises(ApiError) as err:
        ListingService(store, history=ListingHistory(), events=EventBus()).undo_last_edit(stranger, 1)
    assert err.value.code == "FORBIDDEN"


# ---- Mediator --------------------------------------------------------------------
def world():
    store, bus, seen = InMemoryStore(), EventBus(), []
    bus.subscribe(Event, seen.append)
    cust = User(2, "c@x.io", "x", "C", UserRole.CUSTOMER)
    store.users.append(cust)
    store.listings.append(make_listing())
    return store, bus, seen, cust


def test_mediator_coordinates_availability_pricing_storage_and_events():
    store, bus, seen, cust = world()
    availability = ListingService(store).availability
    mediator = BookingMediator(store, availability, bus, FlatFee(DEFAULT_QUOTE, 10))
    booking = mediator.place(store.listings[0], cust.id, date(2027, 5, 1), date(2027, 5, 3),
                             2, D, None, None)
    assert booking.total_price == 210 and store.bookings == [booking]
    assert isinstance(seen[0], BookingConfirmed) and seen[0].host_id == 1


def test_mediator_rejects_unavailable_stays_without_side_effects():
    store, bus, seen, cust = world()
    mediator = BookingMediator(store, ListingService(store).availability, bus, DEFAULT_QUOTE)
    with pytest.raises(ApiError) as err:
        mediator.place(store.listings[0], cust.id, date(2027, 5, 1), date(2027, 5, 3), 99, D, None, None)
    assert err.value.code == "VALIDATION_ERROR" and err.value.field == "check_out"
    mediator.place(store.listings[0], cust.id, date(2027, 5, 1), date(2027, 5, 3), 2, D, None, None)
    with pytest.raises(ApiError) as clash:
        mediator.place(store.listings[0], cust.id, date(2027, 5, 2), date(2027, 5, 4), 2, D, None, None)
    assert clash.value.code == "CONFLICT" and len(store.bookings) == 1 and len(seen) == 1


def test_booking_service_delegates_to_the_mediator():
    store, bus, seen, cust = world()
    booking = BookingService(store, events=bus).book(cust, 1, date(2027, 5, 1), date(2027, 5, 3), 2, D)
    assert booking.id == 1 and len(seen) == 1
