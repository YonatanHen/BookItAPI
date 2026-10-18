# BookIt – Architecture

## Layers and request flow

```mermaid
flowchart TB
    client["HTTP client<br/>(Postman / curl)"]

    subgraph proc["Django process (gunicorn worker)"]
        direction TB
        subgraph mw["Middleware chain: outer → inner"]
            direction TB
            m1["CorrelationIdMiddleware<br/>X-Correlation-ID + ContextVar"]
            m2["RequestLoggingMiddleware<br/>method · path · status · duration"]
            m3["ExceptionHandlingMiddleware<br/>unhandled error → 500 Problem Details"]
            m4["SecurityMiddleware · CommonMiddleware"]
            m5["IdempotencyMiddleware<br/>POST /appointments · hash → TTL"]
            m1 --> m2 --> m3 --> m4 --> m5
        end

        router["URL router<br/>/api/v1/ → namespace v1 (NamespaceVersioning)"]

        subgraph api["API layer · bookit/api/v1"]
            direction TB
            authn["JWTAuthentication + IsAuthenticated<br/>401 no/invalid token"]
            views["Views<br/>auth · businesses · appointments · summary"]
            schemas["Pydantic schemas<br/>request validation · response shape"]
            handler["DRF exception handler<br/>domain errors → Problem Details"]
        end

        subgraph services["Service layer · bookit/services"]
            direction TB
            s1["AuthService"]
            s2["BusinessService"]
            s3["AppointmentService"]
            s4["IdempotencyService"]
            s5["SeedService"]
        end

        orm["Django ORM · bookit/models<br/>User · Business · Service · Appointment · IdempotencyRecord"]
        cfg["config/settings.py<br/>reads .env (secrets never in code)"]
    end

    db[("PostgreSQL 16")]
    envfile[/".env (gitignored)<br/>created from .env.example"/]
    cli["manage.py seed<br/>manage.py purge_idempotency_keys"]
    tests["pytest service tests<br/>fixed clock · no HTTP"]

    client --> m1
    m5 --> router --> authn --> views
    views <--> schemas
    views --> s1
    views --> s2
    views --> s3
    m5 --> s4
    views -. "domain exceptions" .-> handler
    s1 --> orm
    s2 --> orm
    s3 --> orm
    s4 --> orm
    s5 --> orm
    orm --> db
    envfile --> cfg
    cli --> s5
    cli --> s4
    tests --> s3
    tests --> s2
    tests --> s1
```

| Layer | Folder | Responsibility | Must not |
|---|---|---|---|
| Middleware | `bookit/middleware/` | correlation id, request logs, last-resort 500, duplicate-booking guard | contain booking rules |
| API | `bookit/api/v1/` | routing, JWT auth, Pydantic parse/format, status codes | contain business rules or ORM queries |
| Services | `bookit/services/` | business rules, ownership, transactions, domain errors | import DRF or read HTTP objects |
| Models | `bookit/models/` | tables, enums, DB constraints | contain request logic |
| Config | `config/` | settings from env / `.env` | contain secret values |

**Dependency injection:**
- Services receive collaborators in the constructor (for example `clock=timezone.now`).
- Views get the services from `api/v1/dependencies.py`.
- Tests create the services directly with a fixed clock.

**Versioning:**
- `bookit/api/urls.py` mounts `v1/` with `namespace="v1"`.
- A future `v2/` package gets its own urls, views and schemas and reuses the same services.

## Booking sequence (with idempotency)

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant MW as IdempotencyMiddleware
    participant V as AppointmentListCreateView
    participant S as AppointmentService
    participant DB as PostgreSQL

    C->>MW: POST /api/v1/appointments (Bearer JWT, JSON body)
    MW->>MW: user_id from JWT, key = sha256(user_id:POST:path:canonical body)
    MW->>DB: purge expired keys (at most every 5 min), DELETE expired same key
    MW->>DB: INSERT idempotency_records(key, expires_at = now + TTL)
    alt key already exists and not expired
        MW-->>C: 409 Duplicate booking request
    else key stored
        MW->>V: forward request
        V->>V: parse_body(AppointmentCreateRequest)
        V->>S: book(client, service_id, start_time)
        S->>DB: BEGIN, SELECT service FOR UPDATE
        S->>DB: overlapping non-cancelled appointment?
        alt slot taken
            S-->>V: ConflictError
            V-->>MW: 409 slot taken
            MW->>DB: DELETE key (release)
        else slot free
            S->>DB: INSERT appointment (Pending), COMMIT
            V-->>MW: 201 appointment
        end
        MW-->>C: response
    end
```

## Error flow

```mermaid
flowchart LR
    e1["Pydantic ValidationError"] --> h["problem_details_exception_handler"]
    e2["Domain error<br/>NotFound · PermissionDenied · Conflict · BusinessRule · InvalidCredentials"] --> h
    e3["DRF APIException<br/>401 · 403 · 404 · 415 · 429"] --> h
    h --> r1["4xx application/problem+json"]
    e4["Any other exception"] --> m["ExceptionHandlingMiddleware"] --> r2["500 application/problem+json<br/>(traceback only in server log)"]
```
