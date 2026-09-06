"""Shared HTTP client provider for outbound API calls."""

from collections.abc import Generator

import httpx

from app.core.config import settings


def get_deezer_client() -> Generator[httpx.Client, None, None]:
    client = httpx.Client(
        base_url=settings.deezer_base_url,
        timeout=settings.deezer_timeout_seconds,
    )
    try:
        yield client
    finally:
        client.close()
