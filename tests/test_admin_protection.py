"""Garantia de proteção de toda rota sob /api/v1/admin (T-E10.BE.01)."""

import re

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient

from app.api.routes import admin
from app.core.errors import register_exception_handlers
from app.db.session import get_db
from app.main import app
from tests.factories import auth_headers

ADMIN_PREFIX = "/api/v1/admin"
PROBE_PATH = f"{ADMIN_PREFIX}/__probe__"
ANY_ID = "00000000-0000-0000-0000-000000000000"


def _admin_endpoints():
    return [
        pytest.param(method, route.path, id=f"{method} {route.path}")
        for route in iter_route_contexts(app.routes)
        if route.path.startswith(ADMIN_PREFIX)
        for method in sorted(route.methods or ())
    ]


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", ANY_ID, path)


@pytest.mark.parametrize(("method", "path"), _admin_endpoints())
def test_admin_route_without_token_returns_401(client, method, path):
    resp = client.request(method, _concrete(path))

    assert resp.status_code == 401


@pytest.mark.parametrize(("method", "path"), _admin_endpoints())
def test_admin_route_with_common_user_returns_403(client, common_user, method, path):
    resp = client.request(method, _concrete(path), headers=auth_headers(common_user))

    assert resp.status_code == 403


@pytest.fixture
def probe_client(db):
    def probe() -> dict:
        return {"probe": "ok"}

    router = APIRouter(
        prefix=admin.router.prefix,
        tags=admin.router.tags,
        dependencies=admin.router.dependencies,
    )
    router.add_api_route("/__probe__", probe, methods=["GET"])

    probe_app = FastAPI()
    register_exception_handlers(probe_app)
    probe_app.include_router(router, prefix="/api/v1")
    probe_app.dependency_overrides[get_db] = lambda: db

    with TestClient(probe_app) as test_client:
        yield test_client


def test_new_admin_route_without_token_returns_401(probe_client):
    resp = probe_client.get(PROBE_PATH)

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_new_admin_route_with_common_user_returns_403(probe_client, common_user):
    resp = probe_client.get(PROBE_PATH, headers=auth_headers(common_user))

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_new_admin_route_with_admin_runs_handler(probe_client, admin_user):
    resp = probe_client.get(PROBE_PATH, headers=auth_headers(admin_user))

    assert resp.status_code == 200
    assert resp.json() == {"probe": "ok"}


def test_admin_tag_is_documented(client):
    spec = client.get("/openapi.json").json()

    assert "admin" in {tag["name"] for tag in spec["tags"]}
