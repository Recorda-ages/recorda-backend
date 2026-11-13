import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import AppUser
from app.models.app_user import ROLE_ADMIN, STATUS_ACTIVE

PRESET_ADMINS = (
    ("admin.camana", "admin.camana@recorda.app", "Eduardo Camana", "Rc!Cm7vQ2xK9pL4w"),
    ("admin.diogo", "admin.diogo@recorda.app", "Diogo Camargo", "Rc!Dg3nT8bY5hF6j"),
    (
        "admin.fensterseifer",
        "admin.fensterseifer@recorda.app",
        "Eduardo Fensterseifer",
        "Rc!Fs9zW4mR2cU7e",
    ),
    ("admin.vitor", "admin.vitor@recorda.app", "Vitor Martins", "Rc!Vt5kH1sG8dN3q"),
    ("admin.toneto", "admin.toneto@recorda.app", "Rafael Toneto", "Rc!Tn2jB6xP9aE4y"),
)


def upsert_admin(db, username: str, email: str, name: str, password: str) -> str:
    existing = db.scalar(
        select(AppUser).where(func.lower(AppUser.username) == username.lower())
    )
    if existing is None:
        existing = db.scalar(
            select(AppUser).where(func.lower(AppUser.email) == email.lower())
        )

    if existing is None:
        db.add(
            AppUser(
                username=username,
                email=email,
                name=name,
                password_hash=hash_password(password),
                role=ROLE_ADMIN,
                status=STATUS_ACTIVE,
            )
        )
        return "criado"

    existing.role = ROLE_ADMIN
    existing.status = STATUS_ACTIVE
    existing.deleted_at = None
    existing.password_hash = hash_password(password)
    return "atualizado"


def main() -> None:
    db = SessionLocal()
    try:
        for username, email, name, password in PRESET_ADMINS:
            outcome = upsert_admin(db, username, email, name, password)
            print(f"{username}: {outcome}")
        db.commit()
        print(f"{len(PRESET_ADMINS)} administradores configurados.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
