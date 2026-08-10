"""Playlist/Channel expander.

Minimal helper to turn a playlist/channel URL into individual video URLs.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess


_YOUTUBE_URL_RE = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/", re.IGNORECASE)


def validate_youtube_url(value: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError("URL is required")
    if not _YOUTUBE_URL_RE.search(v):
        raise ValueError("Invalid YouTube URL")
    return v


def expand_playlist_or_channel(url: str, timeout_sec: int = 60) -> list[dict]:
    """Return items like: {youtube_url, title}.

    Raises:
      - ValueError: invalid URL
      - RuntimeError: yt-dlp missing or failed
      - subprocess.TimeoutExpired: expansion timed out
    """

    url = validate_youtube_url(url)

    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is not installed")

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "-J",
        "--no-warnings",
        "--skip-download",
        url,
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(f"yt-dlp failed: {stderr or 'unknown error'}")

    try:
        data = json.loads(completed.stdout)
    except Exception as e:
        raise RuntimeError("Failed to parse yt-dlp JSON") from e

    entries = data.get("entries") or []
    items: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        entry_id = entry.get("id")
        title = entry.get("title")
        webpage_url = entry.get("webpage_url")

        youtube_url = None
        if isinstance(webpage_url, str) and webpage_url:
            youtube_url = webpage_url
        elif isinstance(entry_id, str) and entry_id:
            youtube_url = f"https://www.youtube.com/watch?v={entry_id}"

        if youtube_url:
            items.append({"youtube_url": youtube_url, "title": title})

    return items
