"""Shared fixtures. No API key is needed for any test."""
from __future__ import annotations

import pytest

from app.tools.network_data import ensure_database


@pytest.fixture(scope="session", autouse=True)
def database():
    """The synthetic drive-test database (generated once if missing)."""
    return ensure_database()


@pytest.fixture
def tickets_file(tmp_path, monkeypatch):
    """Point the ticket store at a temporary file."""
    path = tmp_path / "tickets.json"
    monkeypatch.setattr("app.tools.tickets._path", lambda: path)
    return path
