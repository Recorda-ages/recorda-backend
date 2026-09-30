"""How stored song previews are exposed by the API.

Deezer preview links expire ~15 minutes after being issued, so the link saved when a
Recorda (or favorite song) was chosen can't be handed out later. Responses carry a stable
API route instead, which issues a fresh link on request. The stored value only records
whether the track had a preview at all.
"""


def track_preview_path(deezer_track_id: str) -> str:
    return f"/api/v1/music/tracks/{deezer_track_id}/preview"


def public_preview_url(
    deezer_track_id: str | None, stored_preview_url: str | None
) -> str | None:
    """The API route for a stored track's preview, or None when it had no preview."""
    if not deezer_track_id or not stored_preview_url:
        return None
    return track_preview_path(deezer_track_id)
