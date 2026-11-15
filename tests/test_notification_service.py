import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.app_user import AppUser
from app.models.follow import STATUS_ACCEPTED
from app.services import notification_service as service
from tests.factories import add_follow, add_recorda, add_user


@pytest.fixture
def dono(db: Session) -> AppUser:
    return add_user(db, "dono_do_perfil")


@pytest.fixture
def visitante(db: Session) -> AppUser:
    return add_user(db, "visitante")


def test_follow_request_notifies_the_profile_owner(
    db: Session, dono: AppUser, visitante: AppUser
):
    follow = add_follow(db, visitante, dono)

    notification = service.notify_follow_request(db, follow)

    assert notification.recipient_id == dono.user_id
    assert notification.sender_id == visitante.user_id
    assert notification.type == "FOLLOW_REQUEST"
    assert notification.follow_id == follow.follow_id
    assert notification.is_read is False


def test_follow_accepted_notifies_who_asked(
    db: Session, dono: AppUser, visitante: AppUser
):
    follow = add_follow(db, visitante, dono, status=STATUS_ACCEPTED)

    notification = service.notify_follow_accepted(db, follow)

    assert notification.recipient_id == visitante.user_id
    assert notification.sender_id == dono.user_id
    assert notification.type == "FOLLOW_ACCEPTED"


def test_new_follower_notifies_the_profile_owner(
    db: Session, dono: AppUser, visitante: AppUser
):
    follow = add_follow(db, visitante, dono, status=STATUS_ACCEPTED)

    notification = service.notify_new_follower(db, follow)

    assert notification.recipient_id == dono.user_id
    assert notification.sender_id == visitante.user_id
    assert notification.type == "NEW_FOLLOWER"


def test_like_notifies_the_recorda_author(
    db: Session, dono: AppUser, visitante: AppUser
):
    recorda = add_recorda(db, dono)

    notification = service.notify_like(db, recorda, visitante.user_id)

    assert notification.recipient_id == dono.user_id
    assert notification.sender_id == visitante.user_id
    assert notification.type == "LIKE"
    assert notification.recorda_id == recorda.recorda_id


def test_comment_notifies_the_recorda_author_with_the_deep_link(
    db: Session, dono: AppUser, visitante: AppUser
):
    recorda = add_recorda(db, dono)
    comment_id = uuid.uuid4()

    notification = service.notify_comment(db, recorda, visitante.user_id, comment_id)

    assert notification.recipient_id == dono.user_id
    assert notification.type == "COMMENT"
    assert notification.comment_id == comment_id


def test_mention_notifies_the_mentioned_user(
    db: Session, dono: AppUser, visitante: AppUser
):
    recorda = add_recorda(db, dono)

    notification = service.notify_mention(db, recorda, visitante.user_id)

    assert notification.recipient_id == visitante.user_id
    assert notification.sender_id == dono.user_id
    assert notification.type == "MENTION"


def test_does_not_notify_yourself(db: Session, dono: AppUser):
    recorda = add_recorda(db, dono)

    assert service.notify_like(db, recorda, dono.user_id) is None
    assert service.list_notifications(db, dono.user_id, limit=20, offset=0).items == []


def test_mark_all_as_read_returns_how_many_changed(
    db: Session, dono: AppUser, visitante: AppUser
):
    recorda = add_recorda(db, dono)
    service.notify_like(db, recorda, visitante.user_id)
    service.notify_mention(db, recorda, visitante.user_id)

    assert service.mark_all_as_read(db, dono.user_id) == 1
    assert service.mark_all_as_read(db, dono.user_id) == 0
