"""Pattern: Memento.

``ListingMemento`` (memento) is an opaque deep snapshot of a listing's state,
``Listing`` is the originator, and ``ListingHistory`` is the caretaker that
stores mementos per listing without ever looking inside them. Used to undo a
host's last edit.
"""
from copy import deepcopy
from dataclasses import dataclass, fields

from .domain import Listing


@dataclass(frozen=True)
class ListingMemento:
    listing_id: int
    _state: dict

    @classmethod
    def capture(cls, listing: Listing) -> "ListingMemento":
        return cls(listing.id, {f.name: deepcopy(getattr(listing, f.name)) for f in fields(listing)})

    def restore(self, listing: Listing) -> None:
        for name, value in self._state.items():
            setattr(listing, name, deepcopy(value))


class ListingHistory:
    def __init__(self, limit: int = 10) -> None:
        self._limit = limit
        self._stacks: dict[int, list[ListingMemento]] = {}

    def save(self, listing: Listing) -> None:
        stack = self._stacks.setdefault(listing.id, [])
        stack.append(ListingMemento.capture(listing))
        del stack[:-self._limit]

    def depth(self, listing_id: int) -> int:
        return len(self._stacks.get(listing_id, []))

    def undo(self, listing: Listing) -> bool:
        stack = self._stacks.get(listing.id)
        if not stack:
            return False
        stack.pop().restore(listing)
        return True


LISTING_HISTORY = ListingHistory()  # shared caretaker (services are built per request)
