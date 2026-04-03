"""
Integration tests for FastAPI routes.
Uses pytest-asyncio + httpx AsyncClient with an in-memory SQLite DB.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from ..api.main import create_app
from ..db.models import Base
from ..db.session import get_db

# ── Test fixtures ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Create test HTTP client with overridden DB dependency."""
    app = create_app()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data


# ── Auth routes ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"

    # Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    return token_data["access_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "correct123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no token


@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient):
    # Register + login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "myuser@example.com", "password": "mypassword123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "myuser@example.com", "password": "mypassword123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "myuser@example.com"


# ── Reports ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reports_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/reports")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reports_returns_empty_list(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "reports@example.com", "password": "password123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "reports@example.com", "password": "password123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_report_not_found(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "notfound@example.com", "password": "password123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "notfound@example.com", "password": "password123"},
    )
    token = login_resp.json()["access_token"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.get(
        f"/api/v1/reports/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
