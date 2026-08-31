"""Tests for the OpenAPI docs contract (Bearer auth scheme, tags, padlocks)."""

AUTH_LOGIN = "/api/v1/auth/login"
AUTH_ME = "/api/v1/auth/me"


def test_openapi_declares_bearer_scheme(client):
    spec = client.get("/openapi.json").json()
    schemes = spec["components"]["securitySchemes"]
    assert schemes, "expected at least one security scheme"
    assert any(
        v.get("type") == "http" and v.get("scheme") == "bearer"
        for v in schemes.values()
    ), "expected an http/bearer security scheme for the Authorize button"


def test_protected_route_requires_bearer_in_docs(client):
    spec = client.get("/openapi.json").json()
    me = spec["paths"][AUTH_ME]["get"]
    assert "security" in me and me["security"], (
        "protected route should carry a security requirement (padlock)"
    )
    assert me["security"][0] == {"HTTPBearer": []}


def test_admin_route_requires_bearer_in_docs(client):
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/api/v1/users"]["get"]
    assert "security" in operation and operation["security"]


def test_public_routes_do_not_require_auth_in_docs(client):
    spec = client.get("/openapi.json").json()
    assert "security" not in spec["paths"]["/api/v1/users"]["post"]
    assert "security" not in spec["paths"][AUTH_LOGIN]["post"]
    assert "security" not in spec["paths"]["/api/v1/health"]["get"]


def test_openapi_groups_endpoints_by_tags(client):
    spec = client.get("/openapi.json").json()
    active_tags = {
        (op.get("tags") or ("_none",))[0]
        for path in spec["paths"].values()
        for op in path.values()
        if isinstance(op, dict) and "responses" in op
    }
    assert "auth" in active_tags
    assert "users" in active_tags
    assert "health" in active_tags
