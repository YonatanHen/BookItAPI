"""Create a local .env from .env.example with a freshly generated DJANGO_SECRET_KEY."""
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SECRET_LINE = re.compile(r"^DJANGO_SECRET_KEY=.*$", re.M)


def create_env_file(root: Path) -> bool:
    """Write root/.env from the template; return False and change nothing if .env already exists."""
    target = root / ".env"
    if target.exists():
        return False
    template = (root / ".env.example").read_text(encoding="utf-8")
    secret = secrets.token_urlsafe(50)
    target.write_text(_SECRET_LINE.sub(lambda _: f"DJANGO_SECRET_KEY={secret}", template, count=1), encoding="utf-8")
    return True


def main() -> int:
    """CLI entry point: create .env in the project root."""
    if create_env_file(ROOT):
        print("Created .env with a new DJANGO_SECRET_KEY. Check the DB_* values match your Postgres container.")
    else:
        print(".env already exists; nothing changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
