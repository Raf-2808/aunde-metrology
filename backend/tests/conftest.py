"""Izolowana baza testowa. PostgreSQL można wskazać TEST_DATABASE_URL."""

import os, sys, pathlib

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite://")
os.environ["COOKIE_SECURE"] = "false"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.models import Base, Session, User, Method
from app.main import app
from app.security import hasher


@pytest.fixture
def client():
    """Tworzy świeży schemat i administratora dla każdego scenariusza."""
    url = os.environ["DATABASE_URL"]
    engine = create_engine(
        url,
        **(
            {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
            if url == "sqlite://"
            else {}
        ),
    )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session.configure(bind=engine)
    with Session() as db:
        db.add(
            User(login="admin", password=hasher.hash("Test_password_123"), role="admin")
        )
        db.add(Method(code="TEST METHOD", name="Metoda testowa"))
        db.commit()
    with TestClient(app) as c:
        r = c.post(
            "/api/login", json={"login": "admin", "password": "Test_password_123"}
        )
        assert r.status_code == 200
        c.headers["x-csrf-token"] = r.json()["csrf"]
        yield c
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def spec():
    return {
        "key": "thickness",
        "name": "Grubość",
        "method_id": 1,
        "unit": "mm",
        "kind": "numeric",
        "count": 3,
        "labels": ["LH", "M", "RH"],
        "lsl": "3.2",
        "usl": "3.8",
        "lower_inclusive": True,
        "upper_inclusive": True,
        "decimals": 2,
        "frequency": "every",
        "every_n": 1,
    }


def setup_order(c, spec, **kwargs):
    """Zakłada artykuł i niezależnie zgłoszone zlecenie."""
    a = c.post(
        "/api/articles",
        json={"code": "TEST", "name": "Artykuł testowy", "specs": [spec]},
    )
    assert a.status_code == 200, a.text
    o = c.post(
        "/api/orders", json={"article_id": a.json()["id"], "lot": "LOT-01", **kwargs}
    )
    assert o.status_code == 200, o.text
    p = c.post(f"/api/orders/{o.json()['id']}/start")
    assert p.status_code == 200, p.text
    return a.json(), o.json(), p.json()


def save(c, o, p, values, ack=True, **kwargs):
    return c.post(
        "/api/sessions",
        json={
            "order_id": o["id"],
            "config_id": p["config_id"],
            "cycle": p["cycle"],
            "test_date": "2026-10-22",
            "values": {"thickness": values},
            "acknowledged": ack,
            **kwargs,
        },
    )


def authorize(c, scope):
    r = c.post("/api/reauth", json={"password": "Test_password_123", "scope": scope})
    assert r.status_code == 200, r.text
