"""
Script de seed do banco de dados.

Uso:
    python scripts/seed.py

Variáveis de ambiente necessárias (via .env):
    DATABASE_URL, ACCESS_TOKEN_SECRET_KEY, PASSWORD_HASH_ITERATIONS
"""

import sys
from pathlib import Path

# Garante que o pacote app seja encontrado ao rodar direto da raiz
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import SessionLocal, init_db
from app.models.music_preference import ARTIST, GENRE, TRACK, MusicPreference
from app.models.recorda import Recorda
from app.models.user import User

# ---------------------------------------------------------------------------
# Dados de seed
# ---------------------------------------------------------------------------

ADMIN_USER = {
    "name": "Administrador",
    "email": "admin@recorda.com",
    "username": "admin",
    "password": "Admin@1234",
    "account_type": "admin",
    "onboarding_completed": True,
}

COMMON_USER = {
    "name": "Usuario comum",
    "email": "usuario@recorda.com",
    "username": "usuario",
    "password": "User@1234",
    "account_type": "common",
    "onboarding_completed": True,
}

SAMPLE_RECORDAS = [
    {
        "midia": "foto_praia.jpg",
        "music": "Lose Yourself",
        "description": "Dia incrível na praia com os amigos.",
        "data": "15/01/2024",
    },
    {
        "midia": "video_show.mp4",
        "music": "Harder, Better, Faster, Stronger",
        "description": "Show do Daft Punk que nunca vou esquecer.",
        "data": "22/03/2024",
    },
    {
        "midia": "foto_formatura.jpg",
        "music": "Good Riddance (Time of Your Life)",
        "description": "Formatura — fim de uma era.",
        "data": "10/07/2024",
    },
]

SAMPLE_PREFERENCES = {
    "genres": [
        {"deezer_id": 132, "name": "Pop"},
        {"deezer_id": 116, "name": "Rap/Hip Hop"},
        {"deezer_id": 152, "name": "Rock"},
    ],
    "artists": [
        {"deezer_id": 27, "name": "Daft Punk"},
        {"deezer_id": 13, "name": "Eminem"},
        {"deezer_id": 145, "name": "Coldplay"},
    ],
    "favorite_track": {"deezer_id": 3135556, "name": "Harder, Better, Faster, Stronger"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(db, data: dict) -> User:
    existing = db.query(User).filter_by(email=data["email"]).first()
    if existing:
        print(f"  [SKIP] Usuário já existe: {data['email']}")
        return existing

    user = User(
        name=data["name"],
        email=data["email"],
        username=data["username"],
        password_hash=hash_password(data["password"]),
        account_type=data["account_type"],
        onboarding_completed=data.get("onboarding_completed", False),
    )
    db.add(user)
    db.flush()
    print(f"  [OK]   Usuário criado: {data['email']} (account_type={data['account_type']})")
    return user


def _create_recordas(db, user: User) -> None:
    for r in SAMPLE_RECORDAS:
        exists = db.query(Recorda).filter_by(music=r["music"]).first()
        if exists:
            print(f"  [SKIP] Recorda já existe: {r['music']}")
            continue
        recorda = Recorda(**r)
        db.add(recorda)
        print(f"  [OK]   Recorda criada: {r['music']}")


def _create_preferences(db, user: User) -> None:
    existing = db.query(MusicPreference).filter_by(user_id=user.id).count()
    if existing:
        print(f"  [SKIP] Preferências musicais já existem para: {user.email}")
        return

    for item in SAMPLE_PREFERENCES["genres"]:
        db.add(MusicPreference(user_id=user.id, kind=GENRE, **item))
    for item in SAMPLE_PREFERENCES["artists"]:
        db.add(MusicPreference(user_id=user.id, kind=ARTIST, **item))
    track = SAMPLE_PREFERENCES["favorite_track"]
    db.add(MusicPreference(user_id=user.id, kind=TRACK, **track))
    print(f"  [OK]   Preferências musicais criadas para: {user.email}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed() -> None:
    print("🌱 Iniciando seed do banco de dados...\n")

    init_db()
    db = SessionLocal()

    try:
        print("→ Criando usuários...")
        admin = _create_user(db, ADMIN_USER)
        common = _create_user(db, COMMON_USER)

        print("\n→ Criando recordas de exemplo...")
        _create_recordas(db, common)

        print("\n→ Criando preferências musicais do usuário comum...")
        _create_preferences(db, common)

        db.commit()
        print("\n✅ Seed concluído com sucesso!")
        print("\nContas criadas:")
        print(f"  Admin   → email: {ADMIN_USER['email']}  | senha: {ADMIN_USER['password']}")
        print(f"  Comum   → email: {COMMON_USER['email']} | senha: {COMMON_USER['password']}")

    except Exception as exc:
        db.rollback()
        print(f"\n❌ Erro durante o seed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
