# BookIt API – Project Rules

## Source of truth
- Read `docs/superpowers/specs/2026-10-18-bookit-api-design.md` before any change; the plan is in `docs/superpowers/plans/`.
- The assignment brief is `docs/HomeAssignment_BookItAPI_Python_Django.pdf`; the spec wins where they differ.

## Architecture
- Flow: middleware → views (`bookit/api/v1`) → services (`bookit/services`) → ORM (`bookit/models`).
- Business logic lives only in services (e.g. `AppointmentService`), never in views or schemas/serializers; views parse input, call one service method, return output.
- Pass dependencies (clock, repositories, settings) into services explicitly, so services are testable without HTTP.
- Writes that must succeed or fail together run inside `transaction.atomic`.
- Services raise domain exceptions and never import DRF or HTTP objects.
- Keep models, services, API and middleware in their own folders.

## Workflow
- TDD: write the failing test first, see it fail, then implement.
- One feature per branch named `dev/<feature>`, created from `master` and fast-forward merged back.
- After adding or changing an endpoint, view, route or schema under `bookit/api/`, run the `postman-sync` subagent in the background and commit the updated collection with the task.
- Never push without asking. Never add Claude / Co-Authored-By attribution to commits or PRs.
- Windows: run Python as `.venv/Scripts/python`; start Postgres with `docker start bookit-db`.

## Code style
- Every production function and class gets a 1–2 line docstring; test functions do not need one.
- Add comments only where the code is not obvious; one line, two at most.
- `.remember/` and `.claude/settings.local.json` stay in `.gitignore`.
- Secrets (e.g. `DJANGO_SECRET_KEY`, `DB_PASSWORD`) live only in the gitignored `.env`; code reads them with no default.