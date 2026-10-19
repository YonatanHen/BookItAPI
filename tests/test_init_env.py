import os
import re
import stat
from pathlib import Path

import pytest

from scripts.init_env import create_env_file

TEMPLATE = "# comment\nDJANGO_SECRET_KEY=\nDB_PASSWORD=bookit\n"


def _secret(path):
    return re.search(r"^DJANGO_SECRET_KEY=(.*)$", path.read_text(encoding="utf-8"), re.M).group(1)


def test_creates_env_from_example_with_generated_secret(tmp_path):
    (tmp_path / ".env.example").write_text(TEMPLATE, encoding="utf-8")
    assert create_env_file(tmp_path) is True
    env_file = tmp_path / ".env"
    assert len(_secret(env_file)) >= 50
    assert "DB_PASSWORD=bookit" in env_file.read_text(encoding="utf-8")
    assert "# comment" in env_file.read_text(encoding="utf-8")


def test_never_overwrites_an_existing_env(tmp_path):
    (tmp_path / ".env.example").write_text(TEMPLATE, encoding="utf-8")
    (tmp_path / ".env").write_text("DJANGO_SECRET_KEY=keep-me\n", encoding="utf-8")
    assert create_env_file(tmp_path) is False
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "DJANGO_SECRET_KEY=keep-me\n"


def test_each_env_gets_a_different_secret(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    for folder in (first, second):
        folder.mkdir()
        (folder / ".env.example").write_text(TEMPLATE, encoding="utf-8")
        create_env_file(folder)
    assert _secret(first / ".env") != _secret(second / ".env")


def test_does_not_overwrite_an_env_created_after_the_check(tmp_path, monkeypatch):
    (tmp_path / ".env.example").write_text(TEMPLATE, encoding="utf-8")
    (tmp_path / ".env").write_text("DJANGO_SECRET_KEY=keep-me\n", encoding="utf-8")
    monkeypatch.setattr(Path, "exists", lambda self: False)
    assert create_env_file(tmp_path) is False
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "DJANGO_SECRET_KEY=keep-me\n"
