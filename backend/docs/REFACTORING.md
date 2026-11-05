# Backend refactoring — checkpoints, patterns, principles

Method: **characterization tests first** (lock current behaviour), then for each
checkpoint **red** (new tests for the new seam) → **green** (move/implement) →
full suite + coverage gate. Public imports (`from app.services import ...`) and
every JSON response shape are unchanged.

Run everything (fails below 100 % line+branch coverage, see `.coveragerc`):

    cd backend && python -m pytest --cov

| CP | What changed | Patterns | Principles |
|----|--------------|----------|------------|
| 0 | Coverage gate + characterization tests (79 % → 100 % reachable) | — | safety net |
| 1 | `services.py` (705 lines) → `services/` package: `navigation`, `pricing`, `completeness`, `stay_window`, `auth/booking/review/analytics/listing_service`; dead branches removed | **Strategy** (`PriceTierStrategy`), Facade (`services/__init__`) | SRP, DIP, DRY |
| 2 | Listing validation and availability become handler chains (`listing_validation.py`, `availability.py`) | **Chain of Responsibility** | OCP, SRP |
| 3 | Booking/listing lifecycles as state objects (`domain.py`); entity creation + id allocation (`factories.py`) | **State**, **Factory Method** | OCP, SRP, DRY |
| 4 | JSON shaping moved from routers to `presenters.py`; `require_role` dependency replaces repeated role checks | Presenter, dependency injection | SRP, DRY, thin controllers |
| 5 | `ListingSearch` with injected geocoder/availability; geocoding providers share one algorithm; `store.create_store` | **Template Method**, **Adapter** (providers), **Singleton** (`STORE`) + Factory | DIP, LSP, OCP |
| 6 | `db.py` per-entity mappers replace the if/elif and 4× duplicated column lists | **Data Mapper** (Strategy per entity), Repository (existing) | SRP, DRY, OCP |

## Extending without modifying
* New listing rule → subclass `ListingRule`, add to `default_rules()`.
* New availability rule → subclass `AvailabilityCheck`, link in `build_availability_chain()`.
* New price tiers → pass another `PriceTierStrategy` to `ListingService`.
* New geocoder → subclass `HttpGeocodingProvider` (`_request_url`, `_parse`).
* New persisted entity → add an `EntityMapper` to `MAPPERS`.

## Testing seams
Services take their collaborators (`geocode=`, `price_tier=`, `validator=`) so
unit tests need no network or patching. Postgres-only tests
(`test_postgres_acceptance.py`) still require `STAYNEST_TEST_DB_URL`.
