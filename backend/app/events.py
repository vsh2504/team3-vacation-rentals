"""Pattern: Observer (+ Singleton for the shared bus).

Services (subjects) publish immutable domain events; subscribers (observers)
react without the services knowing who is listening. A failing observer is
isolated so it can never roll back or break the use-case that raised the event.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Event:
    kind = "event"
    recipient_id = None

    @property
    def message(self) -> str:
        return self.kind


@dataclass(frozen=True)
class BookingEvent(Event):
    booking_id: int
    listing_id: int
    customer_id: int
    host_id: int | None

    @property
    def recipient_id(self):  # type: ignore[override]
        return self.host_id


@dataclass(frozen=True)
class BookingConfirmed(BookingEvent):
    kind = "booking.confirmed"

    @property
    def message(self) -> str:
        return f"Booking #{self.booking_id} confirmed for listing #{self.listing_id}"


@dataclass(frozen=True)
class BookingCancelled(BookingEvent):
    kind = "booking.cancelled"

    @property
    def message(self) -> str:
        return f"Booking #{self.booking_id} was cancelled"


@dataclass(frozen=True)
class BookingCompleted(BookingEvent):
    kind = "booking.completed"

    @property
    def message(self) -> str:
        return f"Booking #{self.booking_id} was completed"


@dataclass(frozen=True)
class ReviewSubmitted(BookingEvent):
    rating: int = 0
    kind = "review.submitted"

    @property
    def message(self) -> str:
        return f"New {self.rating}-star review on listing #{self.listing_id}"


@dataclass(frozen=True)
class ListingModerated(Event):
    listing_id: int
    host_id: int | None
    status: str
    kind = "listing.moderated"

    @property
    def recipient_id(self):  # type: ignore[override]
        return self.host_id

    @property
    def message(self) -> str:
        return f"Listing #{self.listing_id} is now {self.status}"


class EventBus:
    """Subject: keeps the observer registry and fans events out."""

    def __init__(self) -> None:
        self._subscribers: list[tuple[type, Callable]] = []
        self.errors: list[Exception] = []

    def subscribe(self, event_type: type, handler: Callable) -> Callable[[], None]:
        entry = (event_type, handler)
        self._subscribers.append(entry)
        return lambda: self._subscribers.remove(entry)

    def publish(self, event: Event) -> None:
        for event_type, handler in list(self._subscribers):
            if isinstance(event, event_type):
                try:
                    handler(event)
                except Exception as exc:  # observer bugs must not break the publisher
                    self.errors.append(exc)


@dataclass(frozen=True)
class Notification:
    recipient_id: int
    kind: str
    message: str


@dataclass
class NotificationLog:
    """Concrete observer: records a notification for each event with a recipient."""
    items: list[Notification] = field(default_factory=list)

    def on_event(self, event: Event) -> None:
        if event.recipient_id is not None:
            self.items.append(Notification(event.recipient_id, event.kind, event.message))


EVENTS = EventBus()          # process-wide bus (Singleton)
NOTIFICATIONS = NotificationLog()
EVENTS.subscribe(Event, NOTIFICATIONS.on_event)
