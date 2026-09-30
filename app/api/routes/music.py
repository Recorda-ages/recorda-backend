import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.deps import get_current_user
from app.core.http import get_deezer_client
from app.schemas.music import ArtistRead, GenreRead, TrackPreviewRead, TrackRead
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


@router.get("/artists/popular", response_model=list[ArtistRead])
def get_popular_artists(
    client: httpx.Client = Depends(get_deezer_client),
) -> list[ArtistRead]:
    return music_service.get_popular_artists(client)


@router.get("/tracks/popular", response_model=list[TrackRead])
def get_popular_tracks(
    client: httpx.Client = Depends(get_deezer_client),
) -> list[TrackRead]:
    return music_service.get_popular_tracks(client)


@router.get(
    "/tracks/{track_id}/preview",
    response_model=TrackPreviewRead,
    dependencies=[Depends(get_current_user)],
)
def get_track_preview(
    track_id: str = Path(pattern=r"^\d+$"),
    client: httpx.Client = Depends(get_deezer_client),
) -> TrackPreviewRead:
    # Requires login because each uncached id costs a call to Deezer. Returns the link
    # instead of redirecting to it: a player following a redirect would carry the user's
    # Authorization header over to Deezer.
    preview_url = music_service.get_track_preview_url(client, track_id)
    if preview_url is None:
        raise HTTPException(status_code=404, detail="Prévia indisponível")
    return TrackPreviewRead(preview_url=preview_url)


@router.get("/tracks/search", response_model=list[TrackRead])
def search_tracks(
    q: str = Query(min_length=1),
    client: httpx.Client = Depends(get_deezer_client),
) -> list[TrackRead]:
    stripped = q.strip()
    if not stripped:
        return []
    return music_service.search_tracks(client, stripped)
