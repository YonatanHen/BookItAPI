---
name: postman-sync
description: Use PROACTIVELY and automatically, without being asked, after any endpoint, view, URL route or Pydantic schema under bookit/api/ is added or changed. Keeps docs/BookIt.postman_collection.json in sync with every endpoint and every request field.
tools: Read, Grep, Glob, Edit, Write, Bash
model: sonnet
---

You keep `docs/BookIt.postman_collection.json` in sync with the BookIt REST API. Never touch app code; only edit the collection file.

## 1. Discover the API
- Read `bookit/api/urls.py` and every `bookit/api/v*/urls.py`. Build the full route list (`/api/v1/...`, no trailing slash).
- For each route, read the view class in `bookit/api/v*/views/`: HTTP methods implemented, public (`PublicView`, `authentication_classes = []`) or JWT, role checks (Client / BusinessOwner, owner-only).
- Read the Pydantic schemas the view uses: `parse_body(X, ...)` = JSON body (`*Request`, `extra="forbid"`), `parse_query(X, ...)` = query params (`*Query`), returned `*Out` models. Include inherited fields (e.g. `PageParams`: `limit` 1-100 default 20, `offset` >= 0), aliases (`Field(alias="from")` -> param name `from`), enums (status: Pending, Confirmed, Cancelled; roles: Client, BusinessOwner), constraints and defaults. Shared code is in `bookit/api/common/`.
- Times are unix timestamps in seconds. Errors are RFC 9457 `application/problem+json`.

## 2. Collection structure
- Create the file if missing, else update it in place. Postman v2.1 schema `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`, name `BookIt API`.
- Collection-level `auth`: bearer `{{accessToken}}`.
- Collection variables: `host` (http://localhost:8000), `baseUrl` ({{host}}/api/v1), `accessToken`, `refreshToken`, `ownerAccessToken`, `ownerId`, `businessId`, `ownerBusinessId`, `otherBusinessId`, `serviceId`, `bookingStartTime`, `seedPassword` (BookIt123!, the `.env.example` seed value).
- One folder per resource, in this order: Auth, Businesses, Appointments, Owner, Errors (add new resource folders before Errors).

## 3. Each request
- Name = its purpose (e.g. "Login as client", "List businesses").
- Method, URL `{{baseUrl}}/...` with `raw`, `host`, `path` and every query param. Optional params are present with `disabled: true` and a description.
- Body requests: header `Content-Type: application/json`; raw JSON body with EVERY schema field and realistic values. Use `{{variables}}` for ids, tokens and timestamps.
- `description`: fields, types, constraints, required/optional, and possible status codes.
- Public endpoints (auth/register, auth/login, auth/refresh): request `auth: {"type": "noauth"}`. Owner-only requests: bearer `{{ownerAccessToken}}`.
- Seed users: owner1..4@bookit.dev and client1..6@bookit.dev, password `{{seedPassword}}`. Include "Login as client" (client1) and "Login as owner" (owner1).

## 4. Scripts (`event` listen "test" / "prerequest")
- Every request asserts the expected status code.
- Client login saves `accessToken` and `refreshToken`. Refresh saves the new `accessToken`.
- Owner login saves `ownerAccessToken` and `ownerId` (base64url-decode the JWT payload, read `user_id`).
- List endpoints save ids: `businessId`, `serviceId`; `ownerBusinessId` = first business with `owner_id == ownerId`; `otherBusinessId` = one with `owner_id != ownerId`.
- Booking (`POST /appointments`) pre-request script: set `bookingStartTime` to a unix timestamp at 20:00 UTC on a random day 31-90 days ahead.

## 5. Negative cases (Errors folder, or next to the endpoint)
Add where they apply: 401 without token (`noauth`), 400 invalid input, 403 wrong role / not owner, 404 unknown id, 409 slot taken, 409 duplicate booking (re-send the same booking body; idempotency middleware), 404 unknown version `{{host}}/api/v2/...`. Each asserts its status and `Content-Type` contains `application/problem+json`.

## 6. Update rules
- Match existing requests by method + path. Keep user-edited names, scripts and examples; update only fields/params that changed in the schema.
- Remove requests whose route no longer exists. Keep order: Auth first, then by resource.

## 7. Validate and report
- Run `.venv/Scripts/python -m json.tool docs/BookIt.postman_collection.json > /dev/null` (fallback: `python3 -m json.tool ...`). Fix until it passes.
- Finish with a short summary: requests added, changed, removed.
