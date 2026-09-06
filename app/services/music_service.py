"""Business logic for music: proxies Deezer API and maps responses to schemas."""

import httpx
from fastapi import HTTPException

from app.schemas.music import ArtistRead, GenreRead, TrackRead


def get_genres(client: httpx.Client) -> list[GenreRead]:
    try:
        response = client.get("/genre")
        response.raise_for_status()
    except httpx.TimeoutException as err:
        raise HTTPException(status_code=502, detail="Serviço de música indisponível") from err
    except httpx.HTTPError as err:
        raise HTTPException(status_code=502, detail="Serviço de música indisponível") from err

    # All information comes sealed in the data label.
    # Right after get "data", we're able to access id, name and picture_url informations.
    data = response.json().get("data", [])

    # Return all genres with id != 0 as determined by the schema.
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
    try:
        # Params: concatenate the searched artist's name at the end of the URL.
        # example https://api.deezer.com/search/artist?q=Eminem
        resp = client.get("/search/artist", params={"q": q})
        resp.raise_for_status()
    except httpx.TimeoutException as err:
        raise HTTPException(status_code=502, detail="Serviço de música indisponível") from err
    except httpx.HTTPError as err:
        raise HTTPException(status_code=502, detail="Serviço de música indisponível") from err

    data = resp.json().get("data", [])
    return [
        ArtistRead(
            id=a["id"],
            name=a["name"],
            picture_url=a.get("picture_medium") or a.get("picture"),
        )
        for a in data
    ]


def search_tracks(client: httpx.Client, q: str) -> list[TrackRead]:
    try:
        resp = client.get("/search", params={"q": q})
        resp.raise_for_status()
    except httpx.TimeoutException as err:
        raise HTTPException(status_code=502, detail="Serviço de música indisponível") from err
    except httpx.HTTPError as err:
        raise HTTPException(status_code=502, detail="Serviço de música indisponível") from err

    data = resp.json().get("data", [])
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
        for t in data
    ]
