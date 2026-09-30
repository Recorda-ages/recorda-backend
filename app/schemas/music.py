"""Pydantic schemas for music-related responses."""

from pydantic import BaseModel


class GenreRead(BaseModel):
    id: int
    name: str
    picture_url: str | None


class ArtistRead(BaseModel):
    id: int
    name: str
    picture_url: str | None


class TrackPreviewRead(BaseModel):
    """A freshly issued Deezer preview link (Deezer links expire ~15 minutes after issue)."""

    preview_url: str


class TrackRead(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    cover_url: str | None
    preview_url: str | None
    genre_id: int | None
