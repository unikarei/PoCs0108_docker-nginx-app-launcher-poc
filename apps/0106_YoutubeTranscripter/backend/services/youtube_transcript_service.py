"""Retrieve and normalize transcripts supplied by YouTube.

The service deliberately contains the third-party API compatibility code so
the worker can make one small decision: use a usable YouTube transcript or
continue with the existing audio/STT pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Iterable, Optional
from urllib.parse import parse_qs, urlparse

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:  # Keep local utility tests importable before dependency installation.
    YouTubeTranscriptApi = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_UNAVAILABLE_ERRORS = {"NoTranscriptFound", "TranscriptsDisabled"}


@dataclass(frozen=True)
class TranscriptTrack:
    """A selectable YouTube subtitle track summary."""

    language_code: str
    language_name: str
    is_generated: bool
    track: Any = field(repr=False, compare=False)

    def as_dict(self) -> dict[str, Any]:
        """Return only safe metadata for API/database serialization."""
        return {
            "language_code": self.language_code,
            "language_name": self.language_name,
            "is_generated": self.is_generated,
        }


@dataclass
class YouTubeTranscriptResult:
    """Normalized outcome of one YouTube transcript lookup."""

    status: str
    video_id: Optional[str] = None
    text: Optional[str] = None
    language_code: Optional[str] = None
    language_name: Optional[str] = None
    is_generated: Optional[bool] = None
    available_tracks: list[dict[str, Any]] = field(default_factory=list)
    segments: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def usable(self) -> bool:
        """Whether the result contains non-empty transcript text."""
        return self.status == "available" and bool((self.text or "").strip())


def extract_video_id(youtube_url: str) -> str:
    """Extract an 11-character YouTube video ID from supported URL forms."""
    raw = (youtube_url or "").strip()
    if not raw:
        raise ValueError("YouTube URL is required")

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.netloc.lower().split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    if host not in {"youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}:
        raise ValueError("Invalid YouTube URL host")

    video_id: Optional[str] = None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/", 1)[0]
    else:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if not video_id:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0].lower() in {"shorts", "embed", "live"}:
                video_id = parts[1]

    if not video_id or not _VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("Could not extract a valid YouTube video ID")
    return video_id


def _track_value(track: Any, name: str, default: Any = None) -> Any:
    """Read a track attribute while supporting simple dict-based test doubles."""
    if isinstance(track, dict):
        return track.get(name, default)
    return getattr(track, name, default)


def _track_summary(track: Any) -> TranscriptTrack:
    """Convert a library track object to a stable internal summary."""
    language_code = str(_track_value(track, "language_code", ""))
    language_name = str(_track_value(track, "language", "") or language_code)
    is_generated = bool(_track_value(track, "is_generated", False))
    return TranscriptTrack(language_code, language_name, is_generated, track)


def _language_score(code: str, requested_language: str) -> int:
    """Rank languages after manual-vs-generated precedence has been applied."""
    code = (code or "").lower()
    requested = (requested_language or "").lower()
    if code == requested or code.startswith(f"{requested}-"):
        return 0
    if code == "ja" or code.startswith("ja-"):
        return 1
    if code == "en" or code.startswith("en-"):
        return 2
    return 3


def _track_sort_key(track: TranscriptTrack, requested_language: str) -> tuple[int, int, str]:
    """Prefer manual tracks, then the requested/standard language order."""
    return (1 if track.is_generated else 0, _language_score(track.language_code, requested_language), track.language_code)


def _raw_snippets(fetched: Any) -> Iterable[Any]:
    """Return raw snippets from old and new youtube-transcript-api results."""
    snippets = getattr(fetched, "snippets", None)
    if snippets is not None:
        return snippets
    if hasattr(fetched, "to_raw_data"):
        return fetched.to_raw_data()
    return fetched or []


def _normalize_segments(fetched: Any) -> list[dict[str, Any]]:
    """Normalize transcript snippets to start/duration/text dictionaries."""
    segments: list[dict[str, Any]] = []
    for snippet in _raw_snippets(fetched):
        if isinstance(snippet, dict):
            text = str(snippet.get("text") or "").strip()
            start = float(snippet.get("start") or 0)
            duration = float(snippet.get("duration") or 0)
        else:
            text = str(getattr(snippet, "text", "") or "").strip()
            start = float(getattr(snippet, "start", 0) or 0)
            duration = float(getattr(snippet, "duration", 0) or 0)
        if text:
            segments.append({"start": start, "duration": duration, "text": text})
    return segments


def _fetch_track(track: TranscriptTrack) -> list[dict[str, Any]]:
    """Fetch and normalize one selected track."""
    fetched = track.track.fetch() if hasattr(track.track, "fetch") else track.track
    return _normalize_segments(fetched)


def _list_tracks(api: Any, video_id: str) -> list[Any]:
    """Call the supported track-list method across library versions."""
    if hasattr(api, "list"):
        return list(api.list(video_id))
    if hasattr(api, "list_transcripts"):
        return list(api.list_transcripts(video_id))
    raise RuntimeError("Unsupported youtube-transcript-api version")


def retrieve_youtube_transcript(youtube_url: str, requested_language: str) -> YouTubeTranscriptResult:
    """Retrieve the best available YouTube transcript without raising to callers."""
    try:
        video_id = extract_video_id(youtube_url)
    except ValueError as exc:
        return YouTubeTranscriptResult(status="error", error=str(exc))

    try:
        if YouTubeTranscriptApi is None:
            raise RuntimeError("youtube-transcript-api is not installed")
        tracks = [_track_summary(item) for item in _list_tracks(YouTubeTranscriptApi(), video_id)]
    except Exception as exc:  # Third-party errors must trigger audio fallback.
        error_name = type(exc).__name__
        if error_name in _UNAVAILABLE_ERRORS:
            return YouTubeTranscriptResult(status="unavailable", video_id=video_id)
        logger.warning("YouTube transcript retrieval failed for %s: %s", video_id, exc)
        return YouTubeTranscriptResult(status="error", video_id=video_id, error="YouTube transcript retrieval failed")

    available_tracks = [track.as_dict() for track in tracks]
    if not tracks:
        return YouTubeTranscriptResult(status="unavailable", video_id=video_id, available_tracks=available_tracks)

    selected = sorted(tracks, key=lambda item: _track_sort_key(item, requested_language))[0]
    try:
        segments = _fetch_track(selected)
    except Exception as exc:
        logger.warning("Selected YouTube transcript could not be fetched for %s: %s", video_id, exc)
        return YouTubeTranscriptResult(
            status="error",
            video_id=video_id,
            available_tracks=available_tracks,
            error="Selected YouTube transcript could not be retrieved",
        )

    text = " ".join(segment["text"] for segment in segments).strip()
    if not text:
        return YouTubeTranscriptResult(status="unavailable", video_id=video_id, available_tracks=available_tracks)

    return YouTubeTranscriptResult(
        status="available",
        video_id=video_id,
        text=text,
        language_code=selected.language_code,
        language_name=selected.language_name,
        is_generated=selected.is_generated,
        available_tracks=available_tracks,
        segments=segments,
    )
