"""Testy używają wyłącznie jawnie wskazanej testowej bazy lub lokalnej pamięci SQLite."""

import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("PUBLIC_BASE_URL", "https://qr.example.test")
from backend.modele import Baza


# Udostępnia izolowaną sesję SQLite dla testów domeny/API; nie potwierdza semantyki blokad PostgreSQL.
@pytest.fixture
def baza():
    silnik = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Baza.metadata.create_all(silnik)
    with sessionmaker(silnik, expire_on_commit=False)() as sesja:
        yield sesja
    silnik.dispose()
