"""Testes do endpoint GET /api/v1/feed/following (app/api/routes/feed.py)."""

from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services import feed_service


def _override_current_user(fake_user):
    from app.api.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: fake_user


def _override_db():
    from app.db.session import get_db

    app.dependency_overrides[get_db] = lambda: iter([None])


class TestGetFollowingFeedRoute:
    def setup_method(self):
        self.client = TestClient(app)
        self.fake_user = type("FakeUser", (), {"user_id": uuid4()})()
        _override_current_user(self.fake_user)
        _override_db()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_returns_200_with_empty_page(self):
        with patch.object(
            feed_service,
            "get_following_feed",
            return_value=feed_service.FeedPage(items=[], next_cursor=None),
        ):
            response = self.client.get("/api/v1/feed/following")

        assert response.status_code == 200
        assert response.json() == {"items": [], "next_cursor": None}

    def test_invalid_cursor_returns_400(self):
        with patch.object(
            feed_service,
            "get_following_feed",
            side_effect=feed_service.InvalidCursorError("Cursor inválido."),
        ):
            response = self.client.get(
                "/api/v1/feed/following", params={"cursor": "lixo-invalido"}
            )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "BAD_REQUEST"
        assert body["error"]["message"] == "Cursor inválido."

    def test_limit_above_max_returns_422(self):
        response = self.client.get("/api/v1/feed/following", params={"limit": 51})

        assert response.status_code == 422

    def test_limit_below_min_returns_422(self):
        response = self.client.get("/api/v1/feed/following", params={"limit": 0})

        assert response.status_code == 422

    def test_calls_service_with_authenticated_user_id(self):
        with patch.object(
            feed_service,
            "get_following_feed",
            return_value=feed_service.FeedPage(items=[], next_cursor=None),
        ) as mock_get_feed:
            self.client.get("/api/v1/feed/following", params={"limit": 10})

        mock_get_feed.assert_called_once()
        _, kwargs = mock_get_feed.call_args
        assert kwargs["current_user_id"] == self.fake_user.user_id
        assert kwargs["limit"] == 10

    def test_requires_authentication(self):
        app.dependency_overrides.clear()  # remove o override de current_user

        response = self.client.get("/api/v1/feed/following")

        # 401 (ou 403, dependendo de como get_current_user está implementado
        # quando não há token) — ajuste conforme o comportamento real de
        # app.api.deps.get_current_user nesse projeto.
        assert response.status_code in (401, 403)