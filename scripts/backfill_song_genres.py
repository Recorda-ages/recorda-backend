"""Fill missing genres in the configured database. Run after migration 0011."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.genre_backfill_service import backfill_genres


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error("--limit deve estar entre 1 e 10000")
    with (
        SessionLocal() as db,
        httpx.Client(
            base_url=settings.deezer_base_url, timeout=settings.deezer_timeout_seconds
        ) as client,
    ):
        checked, updated = backfill_genres(db, client, limit=args.limit)
    print(f"Faixas consultadas: {checked}; Recordas atualizadas: {updated}")


if __name__ == "__main__":
    main()
