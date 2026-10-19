# BookIt – Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ BUSINESSES : "owns"
    USERS ||--o{ APPOINTMENTS : "books (as client)"
    BUSINESSES ||--o{ SERVICES : "offers"
    SERVICES ||--o{ APPOINTMENTS : "is booked in"
    USERS ||--o{ IDEMPOTENCY_RECORDS : "submits"
    APPOINTMENTS |o--o| IDEMPOTENCY_RECORDS : "guarded by"

    USERS {
        bigint id PK
        varchar email UK "stored lowercase"
        varchar password "PBKDF2 hash"
        varchar full_name
        varchar role "UserRole: Client | BusinessOwner"
    }
    BUSINESSES {
        bigint id PK
        varchar name "trigram GIN index on UPPER(name)"
        varchar category "BusinessCategory enum, indexed"
        bigint owner_id FK "users.id"
    }
    SERVICES {
        bigint id PK
        bigint business_id FK "businesses.id"
        varchar name
        integer duration_minutes "check > 0"
        numeric price "10,2 check >= 0"
    }
    APPOINTMENTS {
        bigint id PK
        bigint service_id FK "services.id, covered by the composite index"
        bigint client_id FK "users.id, covered by the composite index"
        timestamptz start_time "indexes (service_id, start_time) and (client_id, start_time)"
        timestamptz end_time "start + duration, check > start"
        varchar status "AppointmentStatus: Pending | Confirmed | Cancelled"
        timestamptz created_at
    }
    IDEMPOTENCY_RECORDS {
        bigint id PK
        varchar key UK "sha256(user:method:path:payload)"
        bigint user_id FK "users.id"
        bigint appointment_id FK "appointments.id, unique, NULL while in progress"
        timestamptz created_at
        timestamptz expires_at "indexed, TTL"
    }
```

## Enums

| Enum | Column | Values |
|---|---|---|
| `UserRole` | `users.role` | `Client`, `BusinessOwner` |
| `BusinessCategory` | `businesses.category` | `Barber`, `Beauty`, `Fitness`, `Massage`, `Physiotherapy`, `Tutoring` |
| `AppointmentStatus` | `appointments.status` | `Pending`, `Confirmed`, `Cancelled` |

## Notes
- All three enums are Django `TextChoices`. DB check constraints also enforce them.
- `users` keeps only what the API needs. There is no `PermissionsMixin` (no admin, groups or permissions), and `last_login` is disabled because JWT logins are stateless.
- `end_time` is stored, so the overlap check is a simple range query:
  `start_time < new_end AND end_time > new_start AND status <> 'Cancelled'`.
- `idempotency_records` works as a `hash → TTL` dictionary that guards appointment creation:
  - The same user cannot create the same appointment twice within the TTL. This prevents a double charge once payments exist.
  - The row is linked to the appointment it created. `appointment_id` is set after the 201, so each appointment has at most one record.
  - A row whose `expires_at` has passed is ignored and purged.
- All foreign keys use `ON DELETE CASCADE`.
