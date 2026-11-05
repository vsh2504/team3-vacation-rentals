"""State pattern (booking + listing lifecycles) and Factory Method (entities)."""
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.domain import (Booking, BookingStatus, CancelledState, CompletedState,
                        ConfirmedState, Listing, ListingStatus, RemovedListingState,
                        ListingState, Review, User, UserRole, booking_state_for,
                        can_cancel, can_review, listing_state_for)
from app.factories import (BookingFactory, ListingFactory, ReviewFactory,
                           UserFactory, next_id)

NOW = datetime(2027, 1, 1, tzinfo=timezone.utc)


def booking(status=BookingStatus.CONFIRMED, **kw):
    base = dict(id=1, listing_id=1, customer_id=2, check_in=date(2027, 5, 1),
                check_out=date(2027, 5, 3), guests=1, total_price=Decimal("1"), status=status)
    base.update(kw)
    return Booking(**base)


# -- booking state -----------------------------------------------------------
def test_booking_state_lookup():
    assert isinstance(booking_state_for(BookingStatus.CONFIRMED), ConfirmedState)
    assert isinstance(booking_state_for(BookingStatus.CANCELLED), CancelledState)
    assert isinstance(booking_state_for(BookingStatus.COMPLETED), CompletedState)


def test_confirmed_state_can_cancel_and_complete():
    b = booking()
    ConfirmedState().cancel(b, NOW)
    assert b.status == BookingStatus.CANCELLED and b.cancelled_at == NOW
    b2 = booking()
    ConfirmedState().complete(b2)
    assert b2.status == BookingStatus.COMPLETED and b2.cancelled_at is None


@pytest.mark.parametrize("state", [CancelledState(), CompletedState()])
def test_terminal_states_reject_transitions(state):
    b = booking(state.status)
    assert state.cancel(b, NOW) is False and state.complete(b) is False
    assert b.status == state.status and b.cancelled_at is None


def test_only_completed_state_allows_review():
    assert CompletedState().allows_review
    assert not ConfirmedState().allows_review and not CancelledState().allows_review


def test_domain_guards_delegate_to_state():
    assert can_cancel(booking(), 2) == []
    assert can_cancel(booking(BookingStatus.COMPLETED), 2) == ["Only CONFIRMED bookings can be cancelled"]
    assert can_cancel(booking(), 9) == ["Only the booking owner can cancel"]
    assert can_review(booking(BookingStatus.COMPLETED), 2, []) == []
    assert can_review(booking(), 2, []) == ["Reviews are allowed only on COMPLETED (past) bookings"]


# -- listing state -----------------------------------------------------------
@pytest.mark.parametrize("status", [ListingStatus.PENDING_APPROVAL, ListingStatus.APPROVED,
                                    ListingStatus.REJECTED])
def test_active_listing_states_allow_everything(status):
    state = listing_state_for(status)
    assert isinstance(state, ListingState) and state.status == status
    assert state.editable and state.moderatable
    assert state.after_edit() == ListingStatus.PENDING_APPROVAL      # re-moderation
    assert state.after_moderation(True) == ListingStatus.APPROVED
    assert state.after_moderation(False) == ListingStatus.REJECTED
    assert state.after_removal() == ListingStatus.REMOVED


def test_removed_listing_is_terminal():
    state = listing_state_for(ListingStatus.REMOVED)
    assert isinstance(state, RemovedListingState)
    assert not state.editable and not state.moderatable
    assert state.after_removal() == ListingStatus.REMOVED


# -- factories ---------------------------------------------------------------
def test_next_id_is_max_plus_one():
    assert next_id([]) == 1
    assert next_id([booking(id=4), booking(id=9), booking(id=2)]) == 10


def test_user_factory_normalizes_and_hashes():
    user = UserFactory.create([User(7, "x@y.co", "h", "X", UserRole.HOST)], "a@b.co",
                              "password1", "Ann", UserRole.CUSTOMER)
    assert user.id == 8 and user.password_hash.startswith("pbkdf2:")
    assert "password1" not in user.password_hash


def test_listing_factory_starts_pending():
    payload = dict(title="t", description="d", address="a", city="c", state="CA", zip="9",
                   lat=1.0, lng=2.0, price_per_night=Decimal("5"), max_guests=1,
                   bedrooms=1, bathrooms=1)
    li = ListingFactory.create([], host_id=3, payload=payload)
    assert (li.id, li.host_id, li.status) == (1, 3, ListingStatus.PENDING_APPROVAL)


def test_booking_factory_snapshots_location_and_price():
    li = Listing(5, 1, "Loft", "d", "1 Main", "SJ", "CA", "95110", 1.5, 2.5, Decimal("100"),
                 2, 1, 1, check_in_time=time(15), check_out_time=time(11))
    b = BookingFactory.create([], li, customer_id=3, check_in=date(2027, 5, 1),
                              check_out=date(2027, 5, 3), guests=2, today=date(2027, 1, 1))
    assert b.total_price == Decimal("200") and b.status == BookingStatus.CONFIRMED
    assert (b.location_name, b.location_zip, b.location_lat) == ("Loft", "95110", 1.5)
    assert (b.check_in_time, b.check_out_time, b.booked_date) == (time(15), time(11), date(2027, 1, 1))
    custom = BookingFactory.create([b], li, 3, date(2027, 6, 1), date(2027, 6, 2), 1,
                                   date(2027, 1, 1), check_in_time=time(16), check_out_time=time(9))
    assert custom.id == 2 and custom.check_in_time == time(16) and custom.check_out_time == time(9)


def test_review_factory():
    r = ReviewFactory.create([Review(3, 1, 1, 1, 5)], booking(), customer_id=2, rating=4, comment="ok")
    assert (r.id, r.booking_id, r.listing_id, r.rating, r.comment) == (4, 1, 1, 4, "ok")
