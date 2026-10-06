"""Testes de aceite de POST /recordas/{recorda_id}/reports (T-E9.US40.BE.01)."""

import uuid

import pytest
from sqlalchemy import select

from app.api.routes.report import (
    ACCESS_DENIED_MESSAGE,
    DUPLICATE_REPORT_MESSAGE,
    RECORDA_NOT_FOUND_MESSAGE,
    SELF_REPORT_MESSAGE,
)
from app.core.time import now_utc
from app.models import Notification, Report
from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from app.models.report import STATUS_OPEN
from app.schemas.report import MAX_DESCRIPTION_LENGTH
from tests.factories import add_follow, add_recorda, add_user, auth_headers


def _report_url(recorda_id) -> str:
    return f"/api/v1/recordas/{recorda_id}/reports"


def _saved_reports(db) -> list[Report]:
    return list(db.scalars(select(Report)))


def _error_message(response) -> str:
    return response.json()["error"]["message"]


@pytest.fixture
def author(db):
    return add_user(db, "autor")


@pytest.fixture
def recorda(db, author):
    return add_recorda(db, author)


# --------------------------------------------------------------------------- #
# Caminho feliz
# --------------------------------------------------------------------------- #


def test_reporting_public_recorda_creates_open_report(client, db, common_user, recorda):
    response = client.post(
        _report_url(recorda.recorda_id),
        json={"description": "Conteúdo ofensivo"},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"report_id", "status", "created_at"}
    assert body["status"] == STATUS_OPEN

    [report] = _saved_reports(db)
    assert str(report.report_id) == body["report_id"]
    assert report.reporter_id == common_user.user_id
    assert report.recorda_id == recorda.recorda_id
    assert report.description == "Conteúdo ofensivo"
    assert report.status == STATUS_OPEN
    assert report.resolved_at is None


@pytest.mark.parametrize(
    "payload",
    [{"description": ""}, {"description": "   "}, {"description": None}, {}],
    ids=["vazia", "so-espacos", "nula", "ausente"],
)
def test_blank_or_missing_description_is_stored_as_null(
    client, db, common_user, recorda, payload
):
    response = client.post(
        _report_url(recorda.recorda_id),
        json=payload,
        headers=auth_headers(common_user),
    )

    assert response.status_code == 201
    [report] = _saved_reports(db)
    assert report.description is None


def test_description_at_the_limit_is_accepted(client, db, common_user, recorda):
    response = client.post(
        _report_url(recorda.recorda_id),
        json={"description": "a" * MAX_DESCRIPTION_LENGTH},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 201


# --------------------------------------------------------------------------- #
# Regras de negócio
# --------------------------------------------------------------------------- #


def test_reporting_same_recorda_twice_returns_409(client, db, common_user, recorda):
    url = _report_url(recorda.recorda_id)
    headers = auth_headers(common_user)

    first = client.post(url, json={}, headers=headers)
    second = client.post(url, json={}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert _error_message(second) == DUPLICATE_REPORT_MESSAGE
    assert len(_saved_reports(db)) == 1


@pytest.mark.parametrize("is_private", [False, True], ids=["publica", "privada"])
def test_reporting_own_recorda_returns_400(client, db, is_private):
    """Em conta privada também é 400: o autor nunca é barrado pela privacidade."""
    owner = add_user(db, "dono", is_private=is_private)
    own_recorda = add_recorda(db, owner)

    response = client.post(
        _report_url(own_recorda.recorda_id), json={}, headers=auth_headers(owner)
    )

    assert response.status_code == 400
    assert _error_message(response) == SELF_REPORT_MESSAGE
    assert _saved_reports(db) == []


# --------------------------------------------------------------------------- #
# Privacidade
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "has_pending_request", [False, True], ids=["estranho", "pendente"]
)
def test_non_approved_follower_cannot_report_private_recorda(
    client, db, common_user, has_pending_request
):
    private_author = add_user(db, "autor_privado", is_private=True)
    private_recorda = add_recorda(db, private_author)
    if has_pending_request:
        add_follow(db, common_user, private_author, status=STATUS_PENDING)

    response = client.post(
        _report_url(private_recorda.recorda_id),
        json={},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 403
    assert _error_message(response) == ACCESS_DENIED_MESSAGE
    assert _saved_reports(db) == []


def test_approved_follower_can_report_private_recorda(client, db, common_user):
    private_author = add_user(db, "autor_privado", is_private=True)
    private_recorda = add_recorda(db, private_author)
    add_follow(db, common_user, private_author)

    response = client.post(
        _report_url(private_recorda.recorda_id),
        json={},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 201
    assert len(_saved_reports(db)) == 1


# --------------------------------------------------------------------------- #
# Alvo indisponível
# --------------------------------------------------------------------------- #


def test_deleted_recorda_returns_404(client, db, common_user, author):
    deleted_recorda = add_recorda(db, author, deleted_at=now_utc())

    response = client.post(
        _report_url(deleted_recorda.recorda_id),
        json={},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 404
    assert _error_message(response) == RECORDA_NOT_FOUND_MESSAGE


def test_recorda_of_suspended_author_returns_404(client, db, common_user):
    suspended_author = add_user(db, "autor_suspenso", status=STATUS_SUSPENDED)
    hidden_recorda = add_recorda(db, suspended_author)

    response = client.post(
        _report_url(hidden_recorda.recorda_id),
        json={},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 404
    assert _error_message(response) == RECORDA_NOT_FOUND_MESSAGE


def test_unknown_recorda_returns_404(client, db, common_user):
    response = client.post(
        _report_url(uuid.uuid4()), json={}, headers=auth_headers(common_user)
    )

    assert response.status_code == 404
    assert _saved_reports(db) == []


# --------------------------------------------------------------------------- #
# Autenticação e validação
# --------------------------------------------------------------------------- #


def test_unauthenticated_request_returns_401(client, db, recorda):
    response = client.post(_report_url(recorda.recorda_id), json={})

    assert response.status_code == 401
    assert _saved_reports(db) == []


def test_description_over_the_limit_returns_422(client, db, common_user, recorda):
    response = client.post(
        _report_url(recorda.recorda_id),
        json={"description": "a" * (MAX_DESCRIPTION_LENGTH + 1)},
        headers=auth_headers(common_user),
    )

    assert response.status_code == 422
    assert _saved_reports(db) == []


# --------------------------------------------------------------------------- #
# Efeitos colaterais proibidos
# --------------------------------------------------------------------------- #


def test_report_keeps_recorda_visible_and_does_not_notify_author(
    client, db, common_user, recorda
):
    client.post(
        _report_url(recorda.recorda_id), json={}, headers=auth_headers(common_user)
    )

    viewer = add_user(db, "outro_usuario")
    response = client.get(
        f"/api/v1/recordas/{recorda.recorda_id}", headers=auth_headers(viewer)
    )

    assert response.status_code == 200
    db.refresh(recorda)
    assert recorda.deleted_at is None
    assert db.scalars(select(Notification)).all() == []
