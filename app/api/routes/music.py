from fastapi import APIRouter, Depends, Query
import httpx

from app.core.http import get_deezer_client
from app.schemas.music import ArtistRead, GenreRead, TrackRead
from app.services import music_service

router = APIRouter(prefix="/music", tags=["music"])


@router.get("/genres", response_model=list[GenreRead])
def list_genres(client: httpx.Client = Depends(get_deezer_client)) -> list[GenreRead]:
    return music_service.get_genres(client)


@router.get("/artists/search", response_model=list[ArtistRead])
def search_artists(
    q: str = Query(min_length=1),
    client: httpx.Client = Depends(get_deezer_client),
) -> list[ArtistRead]:
    stripped = q.strip()
    if not stripped:
        return []
    return music_service.search_artists(client, stripped)


@router.get("/tracks/search", response_model=list[TrackRead])
def search_tracks(
    q: str = Query(min_length=1),
    client: httpx.Client = Depends(get_deezer_client),
) -> list[TrackRead]:
    stripped = q.strip()
    if not stripped:
        return []
    return music_service.search_tracks(client, stripped)
