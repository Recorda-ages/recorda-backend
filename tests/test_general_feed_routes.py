"""Testes do endpoint GET /api/v1/feed/general (app/api/routes/general_feed.py)."""

from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.feed import FeedPage
from app.services import general_feed_service

EMPTY_PAGE = FeedPage(items=[], next_cursor=None)


class TestGetGeneralFeedRoute:
    def setup_method(self):
        self.client = TestClient(app)
        self.fake_user = type("FakeUser", (), {"user_id": uuid4()})()
        app.dependency_overrides[get_current_user] = lambda: self.fake_user
        app.dependency_overrides[get_db] = lambda: iter([None])

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_returns_200_with_empty_page(self):
        with patch.object(
            general_feed_service, "get_general_feed", return_value=EMPTY_PAGE
        ):
            response = self.client.get("/api/v1/feed/general")

        assert response.status_code == 200
        assert response.json() == {"items": [], "next_cursor": None}

    def test_invalid_cursor_returns_400(self):
        with patch.object(
            general_feed_service,
            "get_general_feed",
            side_effect=general_feed_service.InvalidCursorError("Cursor inválido."),
        ):
            response = self.client.get(
                "/api/v1/feed/general", params={"cursor": "lixo-invalido"}
            )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "BAD_REQUEST"
        assert body["error"]["message"] == "Cursor inválido."

    def test_limit_above_max_returns_422(self):
        response = self.client.get("/api/v1/feed/general", params={"limit": 51})

        assert response.status_code == 422

    def test_limit_below_min_returns_422(self):
        response = self.client.get("/api/v1/feed/general", params={"limit": 0})

        assert response.status_code == 422

    def test_calls_service_with_authenticated_user_and_query_params(self):
        with patch.object(
            general_feed_service, "get_general_feed", return_value=EMPTY_PAGE
        ) as mock_get_feed:
            self.client.get(
                "/api/v1/feed/general", params={"limit": 10, "cursor": "abc"}
            )

        _, kwargs = mock_get_feed.call_args
        assert kwargs["current_user_id"] == self.fake_user.user_id
        assert kwargs["limit"] == 10
        assert kwargs["cursor"] == "abc"
