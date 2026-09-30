"""Business logic for music: proxies Deezer API and maps responses to schemas."""

import re
import time
import unicodedata
from typing import Any

import httpx
from fastapi import HTTPException

from app.schemas.music import ArtistRead, GenreRead, TrackRead

MUSIC_UNAVAILABLE_MESSAGE = "Serviço de música indisponível"

ARTIST_SEARCH_FETCH_LIMIT = 50
ARTIST_SEARCH_RESULT_LIMIT = 25
ARTIST_POPULAR_LIMIT = 25
TRACK_POPULAR_LIMIT = 25

# Deezer preview links expire ~15 minutes after being issued; cache for less than that.
PREVIEW_CACHE_SECONDS = 600
PREVIEW_CACHE_MAX_ENTRIES = 2000
_preview_cache: dict[str, tuple[float, str]] = {}

_NAME_EXACT = 0
_NAME_PREFIX = 1
_NAME_WORD = 2
_NAME_CONTAINS = 3
_NAME_OTHER = 4


def get_genres(client: httpx.Client) -> list[GenreRead]:
    data = _get_data(client, "/genre")

    return [
        GenreRead(
            id=g["id"],
            name=g["name"],
            picture_url=g.get("picture_medium") or g.get("picture"),
        )
        for g in data
        if g.get("id") != 0
    ]


def search_artists(client: httpx.Client, q: str) -> list[ArtistRead]:
    data = _get_data(
        client, "/search/artist", params={"q": q, "limit": ARTIST_SEARCH_FETCH_LIMIT}
    )
    ranked = rank_artists(data, q)[:ARTIST_SEARCH_RESULT_LIMIT]
    return [
        ArtistRead(
            id=a["id"],
            name=a["name"],
            picture_url=a.get("picture_medium") or a.get("picture"),
        )
        for a in ranked
    ]


def get_popular_artists(client: httpx.Client) -> list[ArtistRead]:
    data = _get_data(client, "/chart/0/artists", params={"limit": ARTIST_POPULAR_LIMIT})
    unique = _unique_by(data, lambda a: a.get("id"))[:ARTIST_POPULAR_LIMIT]
    return [
        ArtistRead(
            id=a["id"],
            name=a["name"],
            picture_url=a.get("picture_medium") or a.get("picture"),
        )
        for a in unique
    ]


def get_popular_tracks(client: httpx.Client) -> list[TrackRead]:
    data = _get_data(client, "/chart/0/tracks", params={"limit": TRACK_POPULAR_LIMIT})
    unique = _unique_by(
        data,
        lambda t: (
            normalize(t.get("title", "")),
            normalize((t.get("artist") or {}).get("name", "")),
        ),
    )[:TRACK_POPULAR_LIMIT]
    return [
        TrackRead(
            id=t["id"],
            title=t["title"],
            artist=t["artist"]["name"],
            album=t["album"]["title"],
            cover_url=t["album"].get("cover_medium") or t["album"].get("cover"),
            preview_url=t.get("preview") or None,
            genre_id=t.get("genre_id"),
        )
        for t in unique
    ]


def search_tracks(client: httpx.Client, q: str) -> list[TrackRead]:
    data = _get_data(client, "/search", params={"q": q})
    return [
        TrackRead(
            id=t["id"],
            title=t["title"],
            artist=t["artist"]["name"],
            album=t["album"]["title"],
            cover_url=t["album"].get("cover_medium") or t["album"].get("cover"),
            preview_url=t.get("preview") or None,
            genre_id=t.get("genre_id"),
        )
        for t in rank_tracks(data, q)
    ]


def get_track_preview_url(client: httpx.Client, track_id: str) -> str | None:
    now = time.monotonic()
    cached = _preview_cache.get(track_id)
    if cached and cached[0] > now:
        return cached[1]

    try:
        response = client.get(f"/track/{track_id}")
        response.raise_for_status()
    except httpx.HTTPError as err:
        raise HTTPException(status_code=502, detail=MUSIC_UNAVAILABLE_MESSAGE) from err

    # Unknown ids come back as 200 with an "error" body, so a missing preview covers both.
    preview = response.json().get("preview") or None
    if preview:
        if len(_preview_cache) >= PREVIEW_CACHE_MAX_ENTRIES:
            _preview_cache.clear()
        _preview_cache[track_id] = (now + PREVIEW_CACHE_SECONDS, preview)
    return preview


def rank_artists(artists: list[dict[str, Any]], q: str) -> list[dict[str, Any]]:
    query = normalize(q)
    unique = _unique_by(artists, lambda a: a.get("id"))
    indexed = list(enumerate(unique))
    indexed.sort(
        key=lambda pair: (
            _match_tier(normalize(pair[1].get("name", "")), query),
            -(pair[1].get("nb_fan") or 0),
            pair[0],
        )
    )
    return [artist for _, artist in indexed]


def rank_tracks(tracks: list[dict[str, Any]], q: str) -> list[dict[str, Any]]:
    query = normalize(q)
    unique = _unique_by(
        tracks,
        lambda t: (
            normalize(t.get("title", "")),
            normalize((t.get("artist") or {}).get("name", "")),
        ),
    )
    indexed = list(enumerate(unique))
    indexed.sort(
        key=lambda pair: (
            min(
                _match_tier(normalize(pair[1].get("title", "")), query),
                _match_tier(
                    normalize((pair[1].get("artist") or {}).get("name", "")), query
                ),
                _NAME_WORD,
            ),
            pair[0],
        )
    )
    return [track for _, track in indexed]


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents).strip().casefold()


def _match_tier(name: str, query: str) -> int:
    if not query:
        return _NAME_OTHER
    if name == query:
        return _NAME_EXACT
    if name.startswith(query):
        return _NAME_PREFIX
    if re.search(rf"\b{re.escape(query)}\b", name):
        return _NAME_WORD
    if query in name:
        return _NAME_CONTAINS
    return _NAME_OTHER


def _unique_by(items: list[dict[str, Any]], key) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for item in items:
        item_key = key(item)
        if item_key in seen:
            continue
        seen.add(item_key)
        unique.append(item)
    return unique


def _get_data(
    client: httpx.Client, path: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    try:
        response = client.get(path, params=params) if params else client.get(path)
        response.raise_for_status()
    except httpx.HTTPError as err:
        raise HTTPException(status_code=502, detail=MUSIC_UNAVAILABLE_MESSAGE) from err

    return response.json().get("data", [])
