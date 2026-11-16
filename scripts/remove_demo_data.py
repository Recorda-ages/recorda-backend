import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.demo_data_cleanup import find_demo_users, remove_demo_data
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        users = find_demo_users(db)
        if not users:
            print("Nenhum dado de demonstração encontrado.")
            return
        print("Contas de demonstração encontradas:")
        for user in users:
            print(f"  - {user.username} ({user.email})")
        if "--yes" not in sys.argv:
            print("Nada foi removido. Rode de novo com --yes para confirmar.")
            return
        result = remove_demo_data(db)
        print(
            f"Removidos: {result.users_deleted} usuários e "
            f"{result.recordas_deleted} recordas. "
            f"Desativados (referenciados no log de auditoria): "
            f"{result.users_deactivated}."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
