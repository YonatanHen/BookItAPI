# BookIt API – Design Spec

**Date:** 2026-10-18
**Source requirements:** `docs/HomeAssignment_BookItAPI_Python_Django.pdf`
**Implementation plan:** `docs/superpowers/plans/2026-10-18-bookit-api.md`

## 1. Goal
BookIt is the backend API of an appointment booking platform. Business owners (barbers, physiotherapists, tutors...) list businesses and services. Clients book appointments for those services. There is no frontend. The API is used through HTTP clients, for example the Postman collection.

## 2. Tech stack
- Python 3.12, Django 5.2 LTS, Django REST Framework, `djangorestframework-simplejwt`
- **Pydantic v2** (`pydantic[email]`) for all request validation and response serialization. DRF serializers are not used.
- PostgreSQL 16 (Docker), psycopg 3, Django ORM, Django migrations
- pytest + pytest-django; Faker for seed data; gunicorn in the container

## 3. Architecture
```
HTTP → Middleware chain → DRF view (api/v1) → Service layer (services/) → Django ORM (models/) → PostgreSQL
```
- **Views** do only HTTP work:
  1. Parse the body or query string into a Pydantic request schema (`parse_body` / `parse_query`).
  2. Call one service method.
  3. Build a Pydantic response schema and return `schema.model_dump(mode="json")`.
- **Schemas** (Pydantic models in `api/vN/schemas/`) only validate shape and types, and format output. They contain no business rules.
  - Request schemas use `extra="forbid"`, so an unknown body field → 400. Query schemas use `extra="ignore"`.
  - Response schemas are built explicitly with `from_model(obj)` classmethods, so each output field has a clear source.
  - Shared annotated types live in `api/common/schema_types.py`:
    - `UnixTimestamp`: accepts only an integer number of seconds and returns an aware UTC `datetime`. It serializes back to an `int`.
    - `CaseInsensitiveStatus` / `CaseInsensitiveCategory`: map `pending` → `AppointmentStatus.PENDING` and `barber` → `BusinessCategory.BARBER`. Both are built from one `case_insensitive_enum()` helper.
  - A Pydantic `ValidationError` → 400 Problem Details. Its `errors` field is a list of `{field, message}`.
- **Services** contain all business rules, ownership checks and transactions. They raise domain exceptions (`services/exceptions.py`) and never import DRF views, requests, responses or other HTTP code.
  - The one exception: `AuthService` uses SimpleJWT token classes to create tokens.
- **Dependency injection:**
  - Services receive their collaborators in the constructor, for example `clock: Callable[[], datetime]`.
  - Views get service instances from `api/v1/dependencies.py`.
  - Tests create the services directly, with a fixed clock, and without HTTP.
- **Domain error → HTTP mapping** is done in one place: the DRF exception handler.

### Folder layout
```
config/                     settings, root urls, wsgi
bookit/
  models/                   enums.py, user.py, business.py, service.py, appointment.py, idempotency.py
  services/                 exceptions.py, auth_service.py, business_service.py,
                            appointment_service.py, idempotency_service.py, seed_service.py
  api/
    urls.py                 mounts each version under its own namespace
    common/                 problem.py, exception_handler.py, pagination.py, error_views.py, idempotency.py,
                            schemas.py (base schemas), schema_types.py, parsing.py (parse_body / parse_query)
    v1/                     urls.py (mounts routes/), routes/ (one URLconf per resource), dependencies.py, views/, schemas/
  middleware/               correlation.py, request_logging.py, exception_handling.py
  management/commands/      seed.py, purge_idempotency_keys.py
tests/                      factories.py, conftest.py, test_models/, test_services/, test_api/, test_middleware/
docs/                       erd.md, architecture.md, BookIt.postman_collection.json, superpowers/
```

## 4. Data model
**Enums** (`models/enums.py`, Django `TextChoices`):
- `UserRole`: `Client`, `BusinessOwner`
- `AppointmentStatus`: `Pending`, `Confirmed`, `Cancelled`
- `BusinessCategory`: `Barber`, `Beauty`, `Fitness`, `Massage`, `Physiotherapy`, `Tutoring`

**User** (table `users`) is a custom model on `AbstractBaseUser` only, with no `PermissionsMixin`, because there is no admin and no group permissions.
- Fields: `email` (unique, saved in lowercase), `password` (hashed), `full_name`, `role`.
- `last_login = None` drops the inherited column, because JWT logins are stateless. `is_active` stays the inherited constant `True` attribute, not a column.
- `USERNAME_FIELD = "email"`.
- DB check constraint: `role` must be a `UserRole` value.

**Business** (table `businesses`):
- Fields: `name` (`pg_trgm` GIN index on `UPPER(name)` for `?search=`), `category` (`BusinessCategory` enum, indexed), `owner` → User.
- DB check constraint: `category` must be a `BusinessCategory` value.

**Service** (table `services`):
- Fields: `business` → Business, `name`, `duration_minutes` (> 0), `price` (Decimal 10,2, ≥ 0).

**Appointment** (table `appointments`):
- Fields: `service` → Service, `client` → User, `start_time`, `end_time`, `status`, `created_at`.
- `end_time` is calculated at booking time (`start + duration`). It makes the overlap query a simple range comparison.
- Indexes: `(service, start_time)` and `(client, start_time)`. The FKs have no single-column index (`db_index=False`), because these composites cover them.
- Check constraints:
  - `end_time > start_time`
  - `status` must be a valid enum value

**IdempotencyRecord** (table `idempotency_records`):
- Fields: `key` (sha256 hex of the payload, unique), `user` → User, `appointment` → Appointment (one-to-one, nullable: `NULL` while the request runs, set after the 201), `created_at`, `expires_at` (indexed).
- It works as a shared `hash → TTL` dictionary that guards appointment creation. The same user cannot create the same appointment twice within the TTL, which in theory prevents a double charge.

All foreign keys use `CASCADE`. The ERD is in `docs/erd.md`.

## 5. API (v1)
| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | public | 201 user | 400 validation, 409 email taken |
| POST | `/api/v1/auth/login` | public | 200 `{access, refresh, token_type}` | 400 validation, 401 bad credentials, 429 rate limited (more than `LOGIN_RATE_LIMIT`, default 5/m, per IP) |
| POST | `/api/v1/auth/refresh` | public (refresh token in body) | 200 `{access}` | 400 missing field, 401 invalid/expired refresh |
| GET | `/api/v1/` | JWT | 200 `{version}` | 401 |
| GET | `/api/v1/businesses?category=&search=&order=&limit=&offset=` | JWT | 200 page | 400 bad limit/offset, unknown category or order, 401 |
| POST | `/api/v1/appointments` | JWT (Client) | 201 appointment | 400 validation / past time / unknown service, 401, 403 not a client, 409 slot taken or duplicate booking request |
| GET | `/api/v1/appointments?from=&to=&status=&limit=&offset=` | JWT | 200 page | 400 bad filter, 401 |
| GET | `/api/v1/businesses/{id}/summary` | JWT (owner of that business) | 200 summary | 401, 403 not owner, 404 no such business |

Unknown version (for example `/api/v2/...`) → 404.

### Versioning
- DRF `NamespaceVersioning`. `bookit/api/urls.py` mounts `v1/` with `namespace="v1"`.
- `ALLOWED_VERSIONS = ["v1"]`.
- Each version is a separate package (`api/vN/`) with its own urls, views and Pydantic schemas. All versions share the service layer.
- To add v2:
  1. Create `api/v2/`, reusing v1 modules where nothing changed.
  2. Add one `path("v2/", include(...))` line.
  3. Add `"v2"` to `ALLOWED_VERSIONS`.
- The PDF paths `/api/auth/...` become `/api/v1/auth/...`. The README documents this.

### Authentication & token lifecycle
- SimpleJWT `JWTAuthentication` is the only authentication class.
- Default permission is `IsAuthenticated`. Register, login and refresh set `authentication_classes = []` and `AllowAny`.
- **401 vs 403:**
  - Missing, invalid or expired token → **401** with `WWW-Authenticate: Bearer`.
  - Valid token without permission → **403**: the service layer raises `PermissionDeniedError`.
- Login returns an access token (15 min, `JWT_ACCESS_MINUTES`) and a refresh token (1 day, `JWT_REFRESH_DAYS`).
- Both tokens carry the `user_id` and `role` claims. `AuthService.issue_tokens` adds `role` to the refresh token, and SimpleJWT copies it into every access token created from it.
- `ROTATE_REFRESH_TOKENS = False`:
  - A refresh never extends the session.
  - When the refresh token expires, the client gets 401 and must log in again.
  - While the access token is valid, the user stays logged in.
- Email is matched case-insensitively. It is lowercased on register and on login.
- Refresh is implemented in `AuthService.refresh(refresh_token)` with SimpleJWT `RefreshToken(...).access_token`, not with `TokenRefreshView`. So the input is validated with Pydantic like every other endpoint. An invalid or expired token raises `InvalidCredentialsError` → 401.
- Register validation (Pydantic):
  - `email: EmailStr`
  - `password`: also checked with Django `validate_password` (min length 8, not numeric only)
  - `full_name`: 1–150 characters
  - `role: UserRole`

### Pagination
- Limit/offset pagination. Query schemas inherit `PageParams` (Pydantic): `limit: int = 20` (1–100), `offset: int = 0` (≥ 0).
- Invalid values (`limit=0`, `limit=500`, `offset=-1`, `limit=abc`) → 400. They are not silently corrected.
- `api/common/pagination.py::paginate(queryset, params, request, item_schema)` returns `Page[T]` (a generic Pydantic model): `{count, limit, offset, next, previous, results}`.
  - `count` is the total number of matching rows (`queryset.count()`).
  - `next`/`previous` are absolute URLs, or `null`.

### Businesses list
- `category` must be a `BusinessCategory` name, matched case-insensitively (`barber` = `Barber`). An unknown category → 400 that lists the allowed values. `search` is a case-insensitive substring match on `name`.
- `order` is `asc` (default) or `desc`, case-insensitive, and sorts by `name`; `id` breaks ties in the same direction. Any other value → 400.
- Each item contains `id`, `name`, `category`, `owner_id`, `owner_name`, and `services` (`id`, `name`, `duration_minutes`, `price`). Clients need the service ids to book.
- Queries: `select_related("owner")` + `prefetch_related("services")`. The query count is constant.

### Appointments
- **Time format:** `from`, `to` and the booking `start_time` are **unix timestamps in seconds (UTC)**. Response `start_time`/`end_time` are also unix timestamps.
- **Filters:**
  - `from` ≤ `start_time` ≤ `to`, both inclusive.
  - `from > to` → 400.
  - A non-integer or out-of-range timestamp → 400.
- `status` must be one of the `AppointmentStatus` names, case-insensitive (`pending` = `Pending`). Any other value → 400.
- **Scope** comes from the JWT user:
  - A Client sees appointments where `client = user`.
  - A BusinessOwner sees appointments where `service.business.owner = user`.
- **Response item:** `id`, `status`, `start_time`, `end_time`, `service_id`, `service_name`, `price`, `business_id`, `business_name`, `client_id`, `client_name`.
- No N+1: the list query uses `select_related("service__business", "client")`.
- **Booking** (`AppointmentService.book`) runs inside `transaction.atomic()`:
  1. Role must be `Client`, else 403.
  2. `start_time` must be after `clock()`, else 400.
  3. Lock the service row with `select_for_update(of=("self",))`. Unknown service → 400.
  4. `end_time = start + duration`.
  5. A non-cancelled appointment of the same service with `start < new_end AND end > new_start` → 409.
  6. Create the appointment with status `Pending`.

### Business summary
- 404 if the business does not exist (checked first). 403 if `business.owner != user`.
- For each service: `upcoming_appointments` and `expected_revenue`. Both are computed in one SQL query:
  ```python
  upcoming = Q(appointments__start_time__gt=now, appointments__status__in=[PENDING, CONFIRMED])
  Service.objects.filter(business=b).annotate(
      upcoming_appointments=Count("appointments", filter=upcoming),
      expected_revenue=Coalesce(Sum("price", filter=upcoming), Value(Decimal("0.00")), output_field=DecimalField(12, 2)),
  )
  ```
  `Sum(price)` over the joined rows equals count × price.
- Response: `{business_id, business_name, services: [{service_id, service_name, price, duration_minutes, upcoming_appointments, expected_revenue}]}`.

## 6. Error format
- All errors use RFC 9457 Problem Details with `Content-Type: application/problem+json`:
  `{type: "about:blank", title, status, detail, correlation_id, errors?}`. `errors` contains field-level validation messages.
- The DRF `EXCEPTION_HANDLER` (`problem_details_exception_handler`):
  - maps domain errors: `NotFoundError`→404, `PermissionDeniedError`→403, `ConflictError`→409, `BusinessRuleError`→400, `InvalidCredentialsError`→401
  - maps a Pydantic `ValidationError` → 400 with `errors: [{field, message}]`
  - formats every DRF error in the same shape and keeps headers such as `WWW-Authenticate` and `Retry-After`
  - a malformed JSON body (DRF `ParseError`) → 400
- Django `handler404` / `handler500` return the same JSON when `DEBUG=False`.

## 7. Middlewares (custom, in order)
1. **`CorrelationIdMiddleware`**:
   - Uses the incoming `X-Correlation-ID` if it matches `^[A-Za-z0-9._-]{1,128}$`. Otherwise it generates a uuid4 hex.
   - Stores the id in a `ContextVar` and sets the response header.
   - `CorrelationIdFilter` adds the id to every log record.
2. **`RequestLoggingMiddleware`**:
   - Logs `method path -> status (duration ms)` to the logger `bookit.requests`.
   - Adds `method`, `path`, `status_code`, `duration_ms` and `correlation_id` as `extra` fields.
3. **`ExceptionHandlingMiddleware.process_exception`**:
   - Logs the full traceback to `bookit.errors`.
   - Returns a generic 500 Problem Details response (`"An unexpected error occurred."`), without exception text or stack trace.
   - Ignores `Http404`, `PermissionDenied`, `BadRequest` and `SuspiciousOperation`, because Django already handles them.
4. Django `SecurityMiddleware`, `CommonMiddleware` (`APPEND_SLASH = False`).

Brief requirement 2 (request logging + correlation id header) is covered by `CorrelationIdMiddleware` + `RequestLoggingMiddleware` together.

## 8. Booking idempotency
- **Purpose:**
  - A retry, double-click or network replay must not create a second booking.
  - This prepares for payments: one logical request = at most one charge.
  - When payments are added, the charge happens inside the protected request, so a duplicate request is rejected before it can charge again.
- **Scope:** the `@idempotent` decorator (`api/common/idempotency.py`) on the view handler `AppointmentListCreateView.post`. Other create handlers opt in by adding the decorator.
- **Why a DRF decorator, not a middleware:** DRF authenticates inside the view, after all Django middlewares. The decorator runs after authentication and permissions, so it uses `request.user` (one JWT decode), and unauthenticated requests get 401 before it runs. Payment APIs (Stripe, PayPal) place idempotency the same way: after auth, before the handler.
- **Key:** `sha256(f"{user_id}:{method}:{path}:{material}")`.
  - `material` is the `Idempotency-Key` header value, if the client sent one.
  - Otherwise `material` is the canonical JSON body (`sort_keys=True`, compact separators).
  - A body that is not valid JSON is hashed as raw text.
  - The key uses the user id, not the token, so it stays the same after a token refresh.
- **Storage:** the `IdempotencyRecord` DB table, used as a `hash → expires_at` dictionary. It is not an in-memory dict or a local JSON file:
  - an in-memory dict exists per gunicorn worker and is lost on restart
  - a JSON file has write races between workers and exists only on one container
  - the DB unique constraint makes the "insert if not exists" step atomic across all workers and containers
- **Flow** (`IdempotencyService`):
  1. Delete an expired record with the same key.
  2. Insert `key` with `expires_at = now + TTL`, in its own short transaction.
     - If the insert hits the unique key, the hash already exists and has not expired → the decorator raises `ConflictError` → **409** Problem Details `"Duplicate booking request. The same booking was already submitted."`. The handler does not run.
  3. Run the handler.
     - 2xx → keep the hash until it expires, and link it to the created appointment (`appointment_id` = `response.data["id"]`).
     - non-2xx, or an exception → delete the hash, so a corrected retry runs normally.
- **TTL:** `IDEMPOTENCY_TTL_SECONDS` (default 600). PostgreSQL has no native row TTL, so expired rows are cleaned in three ways:
  1. **On the same key:** before the insert, an expired row with the same hash is deleted. Because of this, an expired hash never blocks a booking, and cleanup is only about table size, not correctness.
  2. **Automatic purge in the app:** `IdempotencyService.claim()` runs `DELETE ... WHERE expires_at <= now` at most once every `IDEMPOTENCY_PURGE_INTERVAL_SECONDS` (default 300) per worker process.
     - The last purge time is stored in a class attribute.
     - The time comes from the injected clock, so tests can control it.
     - The `expires_at` index keeps the delete fast.
     - No cron, extra container or extension is needed.
  3. **Manual / cron:** `manage.py purge_idempotency_keys` does a bulk delete on demand.
- **Relation to the overlap check:** the overlap check still protects the data. The two checks answer different cases:
  - Same user + same payload within the TTL → 409 duplicate request, from the `@idempotent` decorator.
  - A different payload or a different user for a taken slot → 409 slot taken, from the overlap check.
- **Known limitation:** a duplicate gets a 409, not the original 201. A client that lost the first response (for example, a timeout) checks `GET /appointments` to confirm the booking. Future improvement for payments: store the first response and replay it.

## 9. Transactions & DB connections
- `ATOMIC_REQUESTS = False`. Reads run in autocommit.
- Writes that must succeed or fail together run in explicit `transaction.atomic()` blocks in the service layer:
  - booking: lock + overlap check + insert
  - registration
  - seeding
- `CONN_MAX_AGE = 60` + `CONN_HEALTH_CHECKS = True`. Each worker thread keeps one persistent connection and reuses it across requests.
- The README contains the 2–3 sentence answer that the assignment asks for.

## 9a. Configuration & secrets
- All configuration comes from environment variables. `config/settings.py` loads a local `.env` file with `python-dotenv` (`load_dotenv(BASE_DIR / ".env")`).
  - Variables that are already set (for example by Docker Compose) are not overridden.
- **Secrets have no default in code:** `DJANGO_SECRET_KEY` and `DB_PASSWORD`.
  - If one is missing, `env()` raises `ImproperlyConfigured("Missing required environment variable: ... Copy .env.example to .env.")`.
  - Non-secret settings (`DB_HOST`, `DB_PORT`, `JWT_ACCESS_MINUTES`, ...) may have safe local defaults.
- `.env` is gitignored and listed in `.dockerignore`. It is never committed and never copied into the image.
- `.env.example` is committed. It has every variable, an empty `DJANGO_SECRET_KEY`, and a comment line above each group.
- **Initialization:** `python scripts/init_env.py`:
  - copies `.env.example` to `.env`
  - fills `DJANGO_SECRET_KEY` with `secrets.token_urlsafe(50)`
  - never overwrites an existing `.env`
- Compose creates the `db` service from `DB_NAME` / `DB_USER` / `DB_PASSWORD` in `.env` and publishes it on `localhost:${DB_PORT}`. Local tests and `runserver` use it through `docker compose up -d db`.
- Docker Compose:
  - the `api` service reads `env_file: .env` and overrides `DB_HOST=db`
  - the `db` service gets `POSTGRES_PASSWORD: ${DB_PASSWORD}` through compose variable interpolation
- `SIMPLE_JWT.SIGNING_KEY` uses `SECRET_KEY`, so JWTs are signed with the secret from `.env`.

## 10. Seed data
- `python manage.py seed [--reset] [--seed N]` calls `SeedService`. The data is random but reproducible (the random generator and Faker are seeded).
- Data:
  - 4 owners (`owner1..4@bookit.dev`) and 6 clients (`client1..6@bookit.dev`), all with the password from `SEED_USER_PASSWORD` in `.env` (the `.env.example` value is `BookIt123!`; the code has no password literal)
  - 20 businesses spread over all 6 `BusinessCategory` values
  - 50 services (10 businesses × 3 + 10 × 2)
  - 200 appointments on hourly slots from −30 to +30 days, with no overlaps
- Idempotent: if `owner1@bookit.dev` exists, the command does nothing. `--reset` deletes all users first. The cascade also removes businesses, services, appointments and idempotency rows.

## 10a. Testing strategy
- TDD in every task: write the failing test first, see it fail, then implement.
- **Test pyramid:**
  - Most tests are **unit tests of the service classes**. They call the service directly with an injected fixed clock and no HTTP.
  - **Schema** tests check Pydantic validation. **Middleware and exception-handler** tests call each class directly.
  - A **thin API layer** checks only the HTTP contract of each endpoint: status codes, 401/403, response shape and query count.
- Every service class has its own pytest test module. This covers and exceeds the bonus "unit tests for one service class".
- Tests run against the real PostgreSQL test DB (pytest-django) and use a fast MD5 password hasher.

## 11. Delivery
- **Git:**
  - One `dev/<feature>` branch per feature. Each branch starts from the `master` tip and is fast-forward merged into it.
  - TDD: tests come first in every branch.
  - No Claude attribution in commit messages.
- **Docker:** the `Dockerfile` and `docker-compose.yml` start `db` (postgres:16 with a healthcheck) and `api`. The `api` entrypoint runs migrate → seed → gunicorn.
- **README:**
  - setup (compose, or `compose up -d db` + venv)
  - seeded credentials and endpoint table
  - token lifecycle, error format and idempotency (with the payment note)
  - transaction answer and links to the diagrams
- **Postman collection** (`docs/BookIt.postman_collection.json`):
  - covers all endpoints
  - stores tokens and ids automatically
  - includes negative examples (401, 403, 409 slot taken, 409 duplicate booking request)
  - kept in sync by the project subagent `postman-sync` (`.claude/agents/postman-sync.md`). It runs in the background after any change under `bookit/api/` (rule in `CLAUDE.md`) and adds every request with all fields, auth, test scripts and negative cases.
- **Diagrams:** `docs/erd.md` (Mermaid `erDiagram`) and `docs/architecture.md` (Mermaid `flowchart`).
- **Code style:** every function/class has a 1–2 line docstring. Comments only where the code is not obvious.

## 12. Bonus items
- Done as part of the core: refresh token, pytest tests for the service classes, docker-compose, request validation with Pydantic.
- Login rate limiting (done): `django-ratelimit` on `POST /auth/login` only, keyed by client IP, `LOGIN_RATE_LIMIT` (default `5/m`).
  - `block=True` raises `Ratelimited` (a `PermissionDenied`); the exception handler maps it to 429 Problem Details with `Retry-After` = the window length.
  - Counters live in the local-memory cache, so each gunicorn worker counts separately. A shared Redis cache is the production fix.
- Out of scope: logout with a token blacklist.
