"""
Script de seed do banco de dados.

Popula o banco com dados iniciais para desenvolvimento:
  - Gêneros musicais canônicos
  - Usuário administrador
  - Usuário comum com recordas e artistas favoritos de exemplo

Uso:
    python scripts/seed.py

O script é idempotente: pode ser executado múltiplas vezes sem duplicar dados.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.seed_data import GENRE_SEED
from app.db.session import SessionLocal, init_db
from app.models.app_user import ROLE_ADMIN, ROLE_USER, AppUser
from app.models.genre import Genre
from app.models.recorda import PHOTO, Recorda
from app.models.user_favorite_artist import UserFavoriteArtist
from app.models.user_favorite_genre import UserFavoriteGenre

# ---------------------------------------------------------------------------
# Dados de seed
# ---------------------------------------------------------------------------

ADMIN = {
    "username": "admin",
    "email": "admin@recorda.com",
    "name": "Administrador",
    "password": "Admin@1234",
    "role": ROLE_ADMIN,
}

COMMON_USER = {
    "username": "gabriel",
    "email": "gabriel@recorda.com",
    "name": "Gabriel Reis",
    "password": "User@1234",
    "role": ROLE_USER,
}

SAMPLE_ARTISTS = [
    {"deezer_artist_id": "27", "artist_name": "Daft Punk", "artist_image_url": None},
    {"deezer_artist_id": "13", "artist_name": "Eminem", "artist_image_url": None},
    {"deezer_artist_id": "145", "artist_name": "Coldplay", "artist_image_url": None},
]

SAMPLE_RECORDAS = [
    {
        "media_url": "https://exemplo.com/fotos/praia.jpg",
        "media_type": PHOTO,
        "description": "Dia incrível na praia com os amigos.",
        "deezer_track_id": "3135556",
        "song_title": "Harder, Better, Faster, Stronger",
        "song_artist_name": "Daft Punk",
        "song_cover_url": "https://exemplo.com/covers/daftpunk.jpg",
        "song_preview_url": None,
    },
    {
        "media_url": "https://exemplo.com/fotos/formatura.jpg",
        "media_type": PHOTO,
        "description": "Formatura — fim de uma era.",
        "deezer_track_id": "908460",
        "song_title": "Good Riddance (Time of Your Life)",
        "song_artist_name": "Green Day",
        "song_cover_url": "https://exemplo.com/covers/greenday.jpg",
        "song_preview_url": None,
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_genres(db) -> dict[str, uuid.UUID]:
    """Insere os gêneros canônicos; retorna mapa name → genre_id."""
    genre_map: dict[str, uuid.UUID] = {}
    for genre_id, name in GENRE_SEED:
        existing = db.query(Genre).filter_by(name=name).first()
        if existing:
            genre_map[name] = existing.genre_id
            continue
        genre = Genre(genre_id=genre_id, name=name)
        db.add(genre)
        genre_map[name] = genre_id
    print(f"  [OK]   {len(GENRE_SEED)} gêneros verificados/inseridos")
    return genre_map


def _create_user(db, data: dict) -> AppUser:
    existing = db.query(AppUser).filter_by(email=data["email"]).first()
    if existing:
        print(f"  [SKIP] Usuário já existe: {data['email']}")
        return existing

    user = AppUser(
        username=data["username"],
        email=data["email"],
        name=data["name"],
        password_hash=hash_password(data["password"]),
        role=data["role"],
    )
    db.add(user)
    db.flush()
    print(f"  [OK]   Usuário criado: {data['email']}  (role={data['role']})")
    return user


def _seed_favorites(db, user: AppUser, genre_map: dict[str, uuid.UUID]) -> None:
    if db.query(UserFavoriteGenre).filter_by(user_id=user.user_id).first():
        print(f"  [SKIP] Favoritos já existem para: {user.email}")
        return

    for name in ("Pop", "Rock", "Hip Hop / Rap"):
        genre_id = genre_map.get(name)
        if genre_id:
            db.add(UserFavoriteGenre(user_id=user.user_id, genre_id=genre_id))

    for artist in SAMPLE_ARTISTS:
        db.add(UserFavoriteArtist(user_id=user.user_id, **artist))

    print(f"  [OK]   Gêneros e artistas favoritos criados para: {user.email}")


def _seed_recordas(db, user: AppUser) -> None:
    if db.query(Recorda).filter_by(user_id=user.user_id).first():
        print(f"  [SKIP] Recordas já existem para: {user.email}")
        return

    for r in SAMPLE_RECORDAS:
        db.add(Recorda(user_id=user.user_id, **r))
    print(f"  [OK]   {len(SAMPLE_RECORDAS)} recordas criadas para: {user.email}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def seed() -> None:
    print("🌱 Iniciando seed do banco de dados...\n")

    init_db()
    db = SessionLocal()

    try:
        print("→ Inserindo gêneros musicais...")
        genre_map = _seed_genres(db)

        print("\n→ Criando usuários...")
        _create_user(db, ADMIN)
        common = _create_user(db, COMMON_USER)

        print("\n→ Criando favoritos e recordas do usuário comum...")
        _seed_favorites(db, common, genre_map)
        _seed_recordas(db, common)

        db.commit()

        print("\n✅ Seed concluído com sucesso!")
        print("\nContas disponíveis:")
        print(f"  Admin  → {ADMIN['email']}        | senha: {ADMIN['password']}")
        print(f"  Comum  → {COMMON_USER['email']}  | senha: {COMMON_USER['password']}")

    except Exception as exc:
        db.rollback()
        print(f"\n❌ Erro durante o seed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
