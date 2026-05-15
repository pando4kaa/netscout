"""
Tests for auth API endpoints:
  POST /api/auth/register
  POST /api/auth/login
  PATCH /api/auth/me
"""

import unittest
import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["username"] == "newuser"

    def test_register_duplicate_email(self, client, test_user):
        resp = client.post("/api/auth/register", json={
            "email": test_user.email,
            "username": "differentuser",
            "password": "securepass123",
        })
        assert resp.status_code == 400
        assert "Email already registered" in resp.json()["detail"]

    def test_register_duplicate_username(self, client, test_user):
        resp = client.post("/api/auth/register", json={
            "email": "another@example.com",
            "username": test_user.username,
            "password": "securepass123",
        })
        assert resp.status_code == 400
        assert "Username already taken" in resp.json()["detail"]

    def test_register_password_too_short(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "short@example.com",
            "username": "shortpassuser",
            "password": "abc",
        })
        assert resp.status_code == 400
        assert "Password must be at least" in resp.json()["detail"]

    def test_register_username_too_short(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "x@example.com",
            "username": "ab",
            "password": "securepass123",
        })
        assert resp.status_code == 400
        assert "Username must be at least" in resp.json()["detail"]

    def test_register_invalid_email(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "username": "validuser",
            "password": "securepass123",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, test_user):
        resp = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_wrong_password(self, client, test_user):
        resp = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "Invalid email or password" in resp.json()["detail"]

    def test_login_unknown_email(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "anypassword",
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert resp.status_code == 422


class TestUpdateProfile:
    def test_patch_me_enable_notifications(self, client, auth_headers, test_user):
        resp = client.patch(
            "/api/auth/me",
            json={"email_notifications_enabled": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_notifications_enabled"] is True
        assert data["email"] == test_user.email

    def test_patch_me_disable_notifications(self, client, auth_headers):
        resp = client.patch(
            "/api/auth/me",
            json={"email_notifications_enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["email_notifications_enabled"] is False

    def test_patch_me_requires_auth(self, client):
        resp = client.patch(
            "/api/auth/me",
            json={"email_notifications_enabled": True},
        )
        assert resp.status_code == 401

    def test_patch_me_invalid_token(self, client):
        resp = client.patch(
            "/api/auth/me",
            json={"email_notifications_enabled": True},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_patch_me_missing_field(self, client, auth_headers):
        resp = client.patch(
            "/api/auth/me",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_token_roundtrip(self, client):
        """Register → use returned token to patch /me."""
        reg = client.post("/api/auth/register", json={
            "email": "round@example.com",
            "username": "roundtrip",
            "password": "securepass123",
        })
        assert reg.status_code == 200
        token = reg.json()["access_token"]

        patch_resp = client.patch(
            "/api/auth/me",
            json={"email_notifications_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["email"] == "round@example.com"
