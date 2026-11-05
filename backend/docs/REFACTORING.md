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

## Pattern-coverage checkpoints (CP7-CP13)

| CP | Pattern | Where | Test file |
|---|---|---|---|
| 7 | Observer | `events.py` (EventBus, NotificationLog); booking/review/listing services publish | `test_cp7_observer.py` |
| 8 | Decorator | `price_quotes.py` (FlatFee, PercentAdjustment); `RetryingProvider` in `geocoding.py` | `test_cp8_decorator.py` |
| 9 | Composite, Iterator | `services/completeness.py` check tree; `services/chain.py` `ChainLink.__iter__` | `test_cp9_composite_iterator.py` |
| 10 | Memento, Mediator | `listing_history.py` (undo edit); `services/booking_mediator.py` | `test_cp10_memento_mediator.py` |
| 11 | Abstract Factory, Builder | `store.py` backends; `seed.py` `ListingBuilder`, `demo_seed.py` `StayBuilder` | `test_cp11_factory_builder.py` |
| 12 | Strategy, Factory Method, Composite, Facade | `core/security.py`, `navigation.py`, `uploads.py`, `stay_window.py`, `ApiError`, `main.create_app`, `routers/__init__` | `test_cp12_strategy_factory_method.py` |
| 13 | Coverage gate | every file in `app/` must be mapped and tagged `Pattern:` | `test_cp13_pattern_map.py` |

All default behaviour is unchanged: price decorators, retries and event
subscribers are opt-in or side-effect free, and the HTTP contract is identical.

## Frontend patterns (F0-F5)

Run: `cd frontend && npm test` / `npm run test:coverage` (100% gate on the pattern layer).

| Step | Pattern | Where | Tests |
|---|---|---|---|
| F0 | tooling | vitest + jsdom + Testing Library, `src/test/setup.js` | - |
| F1 | Factory, Singleton, Facade, Decorator, Adapter | `src/api/client.js` (`createApi`, `api`, `jsonBody`/`bearer`, `normalizeError`) | `api/client.test.js` |
| F2 | Observer, Memento, Singleton | `src/state/createStore.js`, `authStore.js` (`useAuth`) | `state/state.test.jsx` |
| F3 | Strategy | `src/services/navigation.js` (nav links, home path, badge per role) used by `App.jsx` | `services/navigation.test.js`, `App.test.jsx` |
| F4 | Chain of Responsibility | `src/validation/*` used by SearchPage, AuthPage, BookingForm | `validation/validation.test.js` |
| F5 | Protection Proxy | `src/components/RoleGuard.jsx` used by AdminPage, AnalyticsPage | `components/RoleGuard.test.jsx` |

Not under the unit-coverage gate: the large page components (HostPage,
BookingsPage, ListingDetailPage, HostBookingsPage, MapView, ListingCard,
BookingForm, ReviewForm, AuthPage, SearchPage). They are covered by the
browser acceptance suite (`npm run test:browser`).
