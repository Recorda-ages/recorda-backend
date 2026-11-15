"""CLI adapter for the deterministic development database seed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.development_seed import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_DEMO_PASSWORD,
    seed_database,
)
from app.db.session import SessionLocal


def seed() -> None:
    """Populate the configured non-production database."""
    if settings.environment.lower() == "production":
        raise RuntimeError("O seed de desenvolvimento não pode rodar em produção.")

    demo_password = settings.seed_user_password or DEFAULT_DEMO_PASSWORD
    admin_password = settings.seed_admin_password or DEFAULT_ADMIN_PASSWORD
    db = SessionLocal()

    try:
        print("🌱 Populando o banco de desenvolvimento...")
        result = seed_database(
            db,
            demo_password=demo_password,
            admin_password=admin_password,
        )
        print(
            "✅ Seed concluído: "
            f"{result.users_created} usuários, "
            f"{result.recordas_created} recordas, "
            f"{result.follows_created} follows, "
            f"{result.likes_created} likes e "
            f"{result.comments_created} comentários criados."
        )
        print("Conta demo: gabriel | senha definida em SEED_USER_PASSWORD")
        print("Conta admin: admin | senha definida em SEED_ADMIN_PASSWORD")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
