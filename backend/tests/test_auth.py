"""Test auth: dang ky trung email, mat khau ngan, login sai, /api/auth/me."""

import pytest

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


@pytest.mark.asyncio
async def test_register_success(client):
    res = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpass123",
            "full_name": "New User",
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["user"]["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client, normal_user):
    res = await client.post(
        "/api/auth/register",
        json={
            "email": "user@example.com",
            "password": "newpass123",
            "full_name": "Dup",
        },
    )
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_register_short_password(client):
    res = await client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "ab", "full_name": "Short"},
    )
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_wrong_password(client, normal_user):
    res = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "wrongpass"}
    )
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_login_success(client, normal_user):
    res = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "user123"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_me_requires_token(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_me_returns_profile(client, login, normal_user):
    headers = await login("user@example.com", "user123")
    res = await client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_locked_user_cannot_login(client, normal_user, db_session):
    from sqlalchemy import update

    from app.model.user import User

    await db_session.execute(
        update(User).where(User.id == normal_user.id).values(is_active=False)
    )
    await db_session.commit()

    res = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "user123"}
    )
    assert res.status_code in (400, 401, 403), res.text
