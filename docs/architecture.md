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
            m1 --> m2 --> m3 --> m4
        end

        router["URL router<br/>/api/v1/ → namespace v1 (NamespaceVersioning)"]

        subgraph api["API layer · bookit/api/v1"]
            direction TB
            authn["JWTAuthentication + IsAuthenticated<br/>401 no/invalid token"]
            idem["@idempotent on POST /appointments<br/>hash → TTL · duplicate → 409"]
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
    m4 --> router --> authn --> idem --> views
    views <--> schemas
    views --> s1
    views --> s2
    views --> s3
    idem --> s4
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
| Middleware | `bookit/middleware/` | correlation id, request logs, last-resort 500 (every request) | contain booking rules |
| API | `bookit/api/` | routing, JWT auth, `@idempotent` duplicate-booking guard, Pydantic parse/format, status codes | contain business rules or ORM queries |
| Services | `bookit/services/` | business rules, ownership, transactions, domain errors | import DRF or read HTTP objects |
| Models | `bookit/models/` | tables, enums, DB constraints | contain request logic |
| Config | `config/` | settings from env / `.env` | contain secret values |

**Dependency injection:**
- Services receive collaborators in the constructor (for example `clock=timezone.now`).
- Views get the services from `api/v1/dependencies.py`.
- Tests create the services directly with a fixed clock.

**Versioning:**
- `bookit/api/urls.py` mounts `v1/` with `namespace="v1"`.
- `v1/urls.py` mounts one URLconf per resource from `v1/routes/` (`auth`, `businesses`, `appointments`) with `include()`.
- A future `v2/` package gets its own urls, views and schemas and reuses the same services.

## Booking sequence (with idempotency)

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant D as DRF auth (JWT)
    participant I as @idempotent
    participant V as AppointmentListCreateView.post
    participant S as AppointmentService
    participant DB as PostgreSQL

    C->>D: POST /api/v1/appointments (Bearer JWT, JSON body)
    D->>I: request.user resolved (else 401)
    I->>I: key = sha256(user_id:POST:path:Idempotency-Key or canonical body)
    I->>DB: purge expired keys (at most every 5 min), DELETE expired same key
    I->>DB: INSERT idempotency_records(key, expires_at = now + TTL)
    alt key already exists and not expired
        I-->>C: ConflictError → 409 Duplicate booking request
    else key stored
        I->>V: call handler
        V->>V: parse_body(AppointmentCreateRequest)
        V->>S: book(client, service_id, start_time)
        S->>DB: BEGIN, SELECT service FOR UPDATE
        S->>DB: overlapping non-cancelled appointment?
        alt slot taken
            S-->>I: ConflictError → 409 slot taken
            I->>DB: DELETE key (release)
        else slot free
            S->>DB: INSERT appointment (Pending), COMMIT
            V-->>I: 201 appointment
            I->>DB: UPDATE key SET appointment_id
        end
        I-->>C: response
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
