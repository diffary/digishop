import re

import pytest
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.models import User


class FakeGoogleOAuth:
    def __init__(self, userinfo: dict) -> None:
        self.userinfo = userinfo

    async def authorize_redirect(self, request, redirect_uri):
        return RedirectResponse("https://accounts.google.com/mock", status_code=302)

    async def authorize_access_token(self, request):
        return {"userinfo": self.userinfo}


@pytest.fixture
def fake_google(monkeypatch):
    fake = FakeGoogleOAuth({"email": "GUser@Example.com", "sub": "google-sub-123"})
    monkeypatch.setattr("app.api.oauth.oauth.google", fake)
    return fake


async def test_google_login_redirects(client, fake_google):
    r = await client.get("/auth/google", follow_redirects=False)
    assert r.status_code == 302
    assert "accounts.google.com" in r.headers["location"]


async def test_callback_creates_user_and_redirects_with_code(client, fake_google, db_session):
    r = await client.get("/auth/google/callback", follow_redirects=False)
    assert r.status_code == 302
    location = r.headers["location"]
    assert location.startswith("http://localhost:5173/auth/callback?code=")

    user = await db_session.scalar(select(User).where(User.email == "guser@example.com"))
    assert user is not None
    assert user.google_id == "google-sub-123"
    assert user.password_hash is None


async def test_callback_links_existing_user(client, fake_google, db_session):
    r = await client.post(
        "/auth/register", json={"email": "guser@example.com", "password": "pass12345"}
    )
    assert r.status_code == 201

    r = await client.get("/auth/google/callback", follow_redirects=False)
    assert r.status_code == 302

    users = (await db_session.scalars(select(User).where(User.email == "guser@example.com"))).all()
    assert len(users) == 1
    assert users[0].google_id == "google-sub-123"


def _extract_code(location: str) -> str:
    match = re.search(r"code=([^&]+)", location)
    assert match is not None
    return match.group(1)


async def test_exchange_code_returns_jwt(client, fake_google):
    r = await client.get("/auth/google/callback", follow_redirects=False)
    code = _extract_code(r.headers["location"])

    r = await client.post("/auth/exchange", json={"code": code})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "guser@example.com"


async def test_exchange_code_is_one_time(client, fake_google):
    r = await client.get("/auth/google/callback", follow_redirects=False)
    code = _extract_code(r.headers["location"])

    r = await client.post("/auth/exchange", json={"code": code})
    assert r.status_code == 200

    r = await client.post("/auth/exchange", json={"code": code})
    assert r.status_code == 400


async def test_exchange_garbage_code(client):
    r = await client.post("/auth/exchange", json={"code": "nonsense"})
    assert r.status_code == 400


async def test_code_ttl_set(client, fake_google, fake_redis):
    r = await client.get("/auth/google/callback", follow_redirects=False)
    _extract_code(r.headers["location"])

    keys = await fake_redis.keys("oauth:code:*")
    assert len(keys) == 1
    ttl = await fake_redis.ttl(keys[0])
    assert 0 < ttl <= 60
