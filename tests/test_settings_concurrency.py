"""Real PostgreSQL row locks serialize follows with privacy changes."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppUser, Follow, Notification
from app.models.follow import STATUS_ACCEPTED
from app.models.notification import TYPE_FOLLOW_ACCEPTED, TYPE_NEW_FOLLOWER
from app.repositories import follow_repository, user_repository
from app.schemas.settings import UserSettingsUpdate
from app.services import follow_service, settings_service
from tests.factories import add_user


@pytest.mark.postgres
def test_inflight_follow_is_accepted_when_account_becomes_public(pg_db, monkeypatch):
    owner = add_user(pg_db, "owner", is_private=True)
    sender = add_user(pg_db, "sender")
    owner_id, sender_id = owner.user_id, sender.user_id
    engine = pg_db.get_bind()
    follow_started, settings_started, release_follow = Event(), Event(), Event()
    create = follow_repository.create
    lock = user_repository.get_for_update

    def pause_before_insert(db, follow):
        follow_started.set()
        assert release_follow.wait(timeout=10)
        return create(db, follow)

    def signal_settings_lock(db, user_id):
        settings_started.set()
        return lock(db, user_id)

    def follow():
        with Session(engine) as db:
            return follow_service.create_follow(
                db, owner_id, db.get(AppUser, sender_id)
            )

    def make_public():
        with Session(engine) as db:
            return settings_service.update(
                db, db.get(AppUser, owner_id), UserSettingsUpdate(is_private=False)
            )

    monkeypatch.setattr(follow_repository, "create", pause_before_insert)
    monkeypatch.setattr(user_repository, "get_for_update", signal_settings_lock)
    with ThreadPoolExecutor(max_workers=2) as pool:
        follow_result = pool.submit(follow)
        try:
            assert follow_started.wait(timeout=10)
            settings_result = pool.submit(make_public)
            assert settings_started.wait(timeout=10)
            # PATCH must wait for the in-flight follow before scanning PENDING.
            with pytest.raises(TimeoutError):
                settings_result.result(timeout=0.2)
        finally:
            release_follow.set()
        assert follow_result.result(timeout=10) == "solicitado"
        assert settings_result.result(timeout=10).accepted_requests == 1

    pg_db.expire_all()
    assert owner.is_private is False
    assert pg_db.scalar(select(Follow.status)) == STATUS_ACCEPTED
    assert set(pg_db.scalars(select(Notification.type))) == {
        TYPE_NEW_FOLLOWER,
        TYPE_FOLLOW_ACCEPTED,
    }
