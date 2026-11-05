"""CP13 - Pattern coverage gate.

Every source file under ``app/`` must (1) be listed here with the design
pattern it implements, (2) name that pattern in its module docstring after
``Pattern:``, and (3) really define the listed symbols. Adding a file without
a pattern - or removing the pattern code - fails this test, so pattern
coverage stays at 100%.
"""
import importlib
import pathlib

import pytest

APP = pathlib.Path(__file__).resolve().parents[1] / "app"
GOF, ARCH = "GoF", "Architectural"

# relative path -> (kind, pattern keyword, [symbols that must exist in the module])
PATTERN_MAP = {
    "__init__.py": (GOF, "Facade", ["create_app"]),
    "core/__init__.py": (GOF, "Facade", ["ApiError", "ok", "hash_password"]),
    "core/errors.py": (GOF, "Factory Method", ["ApiError"]),
    "core/security.py": (GOF, "Strategy", ["Pbkdf2Hasher", "HmacTokenCodec"]),
    "db.py": (ARCH, "Data Mapper", ["EntityMapper", "MAPPERS"]),
    "demo_seed.py": (GOF, "Builder", ["StayBuilder"]),
    "domain.py": (GOF, "State", ["BookingState", "ListingState"]),
    "events.py": (GOF, "Observer", ["EventBus", "NotificationLog"]),
    "factories.py": (GOF, "Factory Method", ["BookingFactory", "ListingFactory"]),
    "geocoding.py": (GOF, "Template Method", ["HttpGeocodingProvider", "RetryingProvider"]),
    "listing_history.py": (GOF, "Memento", ["ListingMemento", "ListingHistory"]),
    "main.py": (GOF, "Factory Method", ["create_app"]),
    "presenters.py": (ARCH, "Presenter", ["booking_out", "listing_out"]),
    "price_quotes.py": (GOF, "Decorator", ["FlatFee", "PercentAdjustment"]),
    "repositories.py": (ARCH, "Repository", ["InMemoryStore"]),
    "routers/__init__.py": (GOF, "Composite", ["ROUTERS", "include_all"]),
    "routers/admin.py": (ARCH, "Controller", ["router"]),
    "routers/analytics.py": (ARCH, "Controller", ["router"]),
    "routers/auth.py": (ARCH, "Controller", ["router"]),
    "routers/bookings.py": (ARCH, "Controller", ["router"]),
    "routers/common.py": (GOF, "Singleton", ["STORE", "BACKEND", "require_role"]),
    "routers/listings.py": (ARCH, "Controller", ["router"]),
    "routers/reviews.py": (ARCH, "Controller", ["router"]),
    "routers/uploads.py": (GOF, "Strategy", ["_SIGNATURES"]),
    "schemas.py": (ARCH, "Data Transfer Object", ["RegisterIn", "ListingIn"]),
    "seed.py": (GOF, "Builder", ["ListingBuilder"]),
    "store.py": (GOF, "Abstract Factory", ["StorageBackend", "InMemoryBackend", "SqlBackend"]),
    "services/__init__.py": (GOF, "Facade", ["BookingService", "ListingService"]),
    "services/analytics_service.py": (ARCH, "Service Layer", ["AnalyticsService"]),
    "services/auth_service.py": (ARCH, "Service Layer", ["AuthService"]),
    "services/availability.py": (GOF, "Chain of Responsibility", ["AvailabilityCheck"]),
    "services/booking_mediator.py": (GOF, "Mediator", ["BookingMediator"]),
    "services/booking_service.py": (ARCH, "Service Layer", ["BookingService"]),
    "services/chain.py": (GOF, "Iterator", ["ChainLink"]),
    "services/completeness.py": (GOF, "Composite", ["CheckGroup", "FieldCheck"]),
    "services/listing_search.py": (GOF, "Strategy", ["ListingSearch"]),
    "services/listing_service.py": (ARCH, "Service Layer", ["ListingService"]),
    "services/listing_validation.py": (GOF, "Chain of Responsibility", ["ListingRule"]),
    "services/navigation.py": (GOF, "Strategy", ["NavigationStrategy"]),
    "services/pricing.py": (GOF, "Strategy", ["PriceTierStrategy"]),
    "services/review_service.py": (ARCH, "Service Layer", ["ReviewService"]),
    "services/stay_window.py": (GOF, "Chain of Responsibility", ["StayRule"]),
}


def module_name(rel: str) -> str:
    parts = rel[:-3].split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(["app", *parts])


def source_files() -> set[str]:
    return {p.relative_to(APP).as_posix() for p in APP.rglob("*.py")
            if "__pycache__" not in p.parts}


def test_every_source_file_is_mapped_to_a_pattern():
    assert source_files() == set(PATTERN_MAP)


@pytest.mark.parametrize("rel", sorted(PATTERN_MAP))
def test_file_declares_and_defines_its_pattern(rel):
    kind, keyword, symbols = PATTERN_MAP[rel]
    module = importlib.import_module(module_name(rel))
    doc = module.__doc__ or ""
    assert "Pattern:" in doc, f"{rel} has no 'Pattern:' tag in its module docstring"
    tag = doc.split("Pattern:", 1)[1]
    assert keyword.lower() in tag.lower(), f"{rel} tag does not name {keyword}"
    for symbol in symbols:
        assert hasattr(module, symbol), f"{rel} is missing {symbol}"


def test_pattern_statistics():
    total = len(PATTERN_MAP)
    gof = sum(1 for kind, _, _ in PATTERN_MAP.values() if kind == GOF)
    distinct = {kw for _, kw, _ in PATTERN_MAP.values()}
    assert total == len(source_files())
    assert gof + sum(1 for k, _, _ in PATTERN_MAP.values() if k == ARCH) == total
    assert {"Observer", "Decorator", "Composite", "Iterator", "Mediator", "Memento", "State",
            "Strategy", "Singleton", "Abstract Factory", "Factory Method", "Facade",
            "Template Method", "Builder", "Chain of Responsibility"} <= distinct


def test_adapter_and_decorator_are_declared_in_geocoding():
    from app import geocoding
    tag = geocoding.__doc__.split("Pattern:", 1)[1]
    assert "Adapter" in tag and "Decorator" in tag
    assert hasattr(geocoding, "NominatimProvider") and hasattr(geocoding, "GoogleGeocodingProvider")
