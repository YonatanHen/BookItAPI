"""Fail when an API v1 route has no request in the Postman collection."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = {
    ("GET", "health"),
    ("POST", "auth/register"),
    ("POST", "auth/login"),
    ("POST", "auth/refresh"),
    ("GET", "businesses"),
    ("GET", "businesses/:id/summary"),
    ("GET", "appointments"),
    ("POST", "appointments"),
}


def collection_routes(items: list) -> set[tuple[str, str]]:
    """Collect (method, path) pairs from a collection, normalizing ids and variables in paths."""
    routes = set()
    for item in items:
        if "item" in item:
            routes |= collection_routes(item["item"])
            continue
        request = item["request"]
        path = "/".join(":id" if part.startswith("{{") or part.isdigit() else part for part in request["url"]["path"])
        routes.add((request["method"], path))
    return routes


def main() -> int:
    """Print missing routes and return a non-zero exit code if any exist."""
    collection = json.loads((ROOT / "docs" / "BookIt.postman_collection.json").read_text(encoding="utf-8"))
    missing = REQUIRED - collection_routes(collection["item"])
    for method, path in sorted(missing):
        print(f"missing: {method} /api/v1/{path}")
    print("Postman collection covers all routes." if not missing else f"{len(missing)} route(s) missing.")
    return 1 if missing else 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
