import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.seed import seed
from app.db import engine


@pytest.fixture(autouse=True)
def reset_test_database():
    if os.environ.get("TEST_DATABASE_ALLOWED") != "true" or engine.url.database != "portal_test":
        pytest.fail("Testes exigem banco dedicado portal_test e TEST_DATABASE_ALLOWED=true")
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    if owner.url.database != "portal_test" or (owner.url.host, owner.url.port) != (engine.url.host, engine.url.port):
        owner.dispose()
        pytest.fail("A URL de migração também deve apontar para portal_test na mesma instância")
    with owner.begin() as db:
        tables = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename != 'alembic_version' ")).scalars().all()
        db.execute(text("TRUNCATE " + ", ".join('"' + table + '"' for table in tables) + " CASCADE"))
    owner.dispose()
    seed()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def authenticate(client, email="director@aurora.example.com"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": os.environ["DEMO_PASSWORD"]})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture
def context(client):
    headers = authenticate(client)
    tenant = client.get("/api/v1/me", headers=headers).json()["memberships"][0]["institution_id"]
    return headers, "/api/v1/institutions/" + tenant
