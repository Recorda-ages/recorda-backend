import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.core.time import get_month_utc_bounds, to_local, to_utc
from app.db.session import Base, get_db
from app.main import app
from app.models.app_user import AppUser
from app.models.recorda import Recorda
from app.services.calendar_service import get_monthly_calendar


@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine):
    TestingSessionLocal = sessionmaker(
        bind=sqlite_engine, autoflush=False, autocommit=False
    )
    session: Session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(sqlite_session: Session) -> AppUser:
    user = AppUser(
        user_id=uuid.uuid4(),
        email="calendar@test.com",
        username="caluser",
        name="Calendar User",
        password_hash="hash",
    )
    sqlite_session.add(user)
    sqlite_session.commit()
    sqlite_session.refresh(user)
    return user


@pytest.fixture
def client(sqlite_session: Session, test_user: AppUser):
    def _override_get_db():
        yield sqlite_session

    def _override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_calendar_time_helpers():
    naive_dt = datetime(2026, 11, 10, 15, 30)
    utc_dt = to_utc(naive_dt)
    assert utc_dt.tzinfo == UTC

    local_dt = to_local(naive_dt)
    assert str(local_dt.tzinfo) == "America/Sao_Paulo"

    start_dec, end_dec = get_month_utc_bounds(2026, 12)
    assert start_dec < end_dec


def test_calendar_empty_month(sqlite_session: Session):
    user_id = uuid.uuid4()
    res = get_monthly_calendar(sqlite_session, user_id=user_id, year=2026, month=11)
    assert res.year == 2026
    assert res.month == 11
    assert res.total_memories == 0
    assert res.active_days_count == 0
    assert res.days == []


def test_calendar_timezone_and_grouping(sqlite_session: Session):
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    sp_tz = ZoneInfo("America/Sao_Paulo")
    dt_local = datetime(2026, 11, 10, 23, 59, 0, tzinfo=sp_tz)
    dt_utc = dt_local.astimezone(UTC)

    dt_earlier_local = datetime(2026, 11, 10, 10, 0, 0, tzinfo=sp_tz)
    dt_earlier_utc = dt_earlier_local.astimezone(UTC)

    r1_id = uuid.uuid4()
    r1 = Recorda(
        recorda_id=r1_id,
        user_id=user_id,
        media_url="http://img/1.jpg",
        media_type="PHOTO",
        deezer_track_id="123",
        song_title="Track 1",
        song_artist_name="Artist 1",
        song_cover_url="http://img/cover.jpg",
        created_at=dt_earlier_utc,
    )
    r2 = Recorda(
        recorda_id=uuid.uuid4(),
        user_id=user_id,
        media_url="http://img/2.jpg",
        media_type="VIDEO",
        deezer_track_id="123",
        song_title="Track 2",
        song_artist_name="Artist 2",
        song_cover_url="http://img/cover.jpg",
        created_at=dt_utc,
    )
    r_deleted = Recorda(
        recorda_id=uuid.uuid4(),
        user_id=user_id,
        media_url="http://img/del.jpg",
        media_type="PHOTO",
        deezer_track_id="123",
        song_title="Track Del",
        song_artist_name="Artist Del",
        song_cover_url="http://img/cover.jpg",
        created_at=dt_utc,
        deleted_at=datetime.now(UTC),
    )
    r_other = Recorda(
        recorda_id=uuid.uuid4(),
        user_id=other_user_id,
        media_url="http://img/other.jpg",
        media_type="PHOTO",
        deezer_track_id="123",
        song_title="Track Other",
        song_artist_name="Artist Other",
        song_cover_url="http://img/cover.jpg",
        created_at=dt_utc,
    )

    sqlite_session.add_all([r1, r2, r_deleted, r_other])
    sqlite_session.commit()

    res = get_monthly_calendar(sqlite_session, user_id=user_id, year=2026, month=11)

    assert res.total_memories == 2
    assert res.active_days_count == 1
    assert len(res.days) == 1

    day = res.days[0]
    assert day.date == "2026-11-10"
    assert day.day == 10
    assert day.count == 2
    assert day.first_recorda_id == r1_id
    assert day.thumbnail_url == "http://img/1.jpg"
    assert day.media_type == "PHOTO"


def test_calendar_route_flow_and_validation(
    client: TestClient, sqlite_session: Session, test_user: AppUser
):
    # 1. Validação de mês inválido -> 422
    resp_invalid_month = client.get("/api/v1/users/me/calendar?year=2026&month=13")
    assert resp_invalid_month.status_code == 422

    # 2. Validação de ano inválido -> 422
    resp_invalid_year = client.get("/api/v1/users/me/calendar?year=1900&month=5")
    assert resp_invalid_year.status_code == 422

    # 3. Mês sem publicações -> 200 com lista vazia
    resp_empty = client.get("/api/v1/users/me/calendar?year=2026&month=11")
    assert resp_empty.status_code == 200
    assert resp_empty.json()["total_memories"] == 0

    # 4. Inserir recorda e validar retorno formatado
    sp_tz = ZoneInfo("America/Sao_Paulo")
    dt = datetime(2026, 11, 15, 14, 0, 0, tzinfo=sp_tz).astimezone(UTC)
    rec = Recorda(
        recorda_id=uuid.uuid4(),
        user_id=test_user.user_id,
        media_url="http://img/thumb.jpg",
        media_type="PHOTO",
        deezer_track_id="456",
        song_title="Hit",
        song_artist_name="Star",
        song_cover_url="http://img/cover.jpg",
        created_at=dt,
    )
    sqlite_session.add(rec)
    sqlite_session.commit()

    resp_ok = client.get("/api/v1/users/me/calendar?year=2026&month=11")
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["year"] == 2026
    assert data["month"] == 11
    assert data["total_memories"] == 1
    assert data["active_days_count"] == 1
    assert len(data["days"]) == 1
    assert data["days"][0]["day"] == 15
    assert data["days"][0]["thumbnail_url"] == "http://img/thumb.jpg"
