"""Listing completeness report used by the administrator moderation queue.

Pattern: Composite. A :class:`FieldCheck` (leaf) and a :class:`CheckGroup`
(composite) share ``evaluate(listing) -> {name: bool}`` so checks can be
grouped and nested freely; the report treats the whole tree as one check.

The queue needs enough evidence to assess accuracy before approving, so this
reports the individual checks as well as a percentage score. Media may be
photos or videos (requirement 1.3); contact information may be any of name,
email, or phone.
"""
from typing import Callable, Iterator

from ..domain import Listing


def _text(value) -> bool:
    return bool(str(value or "").strip())


class FieldCheck:
    """Leaf: one named predicate over a listing."""

    def __init__(self, name: str, predicate: Callable[[Listing], bool]) -> None:
        self.name = name
        self._predicate = predicate

    def evaluate(self, listing: Listing) -> dict[str, bool]:
        return {self.name: bool(self._predicate(listing))}

    def __iter__(self) -> Iterator["FieldCheck"]:
        yield self


class CheckGroup:
    """Composite: evaluates children (leaves or groups) in order."""

    def __init__(self, name: str, children: list) -> None:
        self.name = name
        self._children = children

    def evaluate(self, listing: Listing) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for child in self._children:
            results.update(child.evaluate(listing))
        return results

    def __iter__(self) -> Iterator[FieldCheck]:
        for child in self._children:
            yield from child


def _has_contact(l: Listing) -> bool:
    return any(_text(v) for v in (l.host_contact_name, l.host_contact_email, l.host_contact_phone))


COMPLETENESS_TREE = CheckGroup("listing", [
    CheckGroup("details", [
        FieldCheck("title", lambda l: _text(l.title)),
        FieldCheck("description", lambda l: _text(l.description)),
    ]),
    CheckGroup("location", [
        FieldCheck("address", lambda l: _text(l.address)),
        FieldCheck("city", lambda l: _text(l.city)),
        FieldCheck("state", lambda l: _text(l.state)),
        FieldCheck("zip", lambda l: _text(l.zip)),
        FieldCheck("coordinates", lambda l: l.lat is not None and l.lng is not None),
    ]),
    CheckGroup("capacity", [
        FieldCheck("price_per_night", lambda l: l.price_per_night and l.price_per_night > 0),
        FieldCheck("max_guests", lambda l: l.max_guests and l.max_guests >= 1),
    ]),
    CheckGroup("operations", [
        FieldCheck("amenities", lambda l: l.amenities),
        FieldCheck("available_times", lambda l: _text(l.available_times)),
        FieldCheck("operating_hours", lambda l: l.operating_start_time != l.operating_end_time),
        FieldCheck("contact", _has_contact),
    ]),
    CheckGroup("media", [
        FieldCheck("media", lambda l: list(l.photos or []) or list(l.videos or [])),
    ]),
])


def listing_completeness(listing: Listing) -> dict:
    photos = list(getattr(listing, "photos", None) or [])
    videos = list(getattr(listing, "videos", None) or [])
    checks = COMPLETENESS_TREE.evaluate(listing)
    missing = [name for name, present in checks.items() if not present]
    return {
        "complete": not missing,
        "score": round(100 * (len(checks) - len(missing)) / len(checks)),
        "missing": missing,
        "checks": checks,
        "photo_count": len(photos),
        "video_count": len(videos),
        "has_photos": bool(photos),
        "has_videos": bool(videos),
    }
