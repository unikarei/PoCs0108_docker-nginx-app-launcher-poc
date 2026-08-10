"""Transcript merging utilities for chunked transcription.

This module merges chunk-level transcription results into a single continuous transcript.
- Applies chunk time offsets so segment timestamps are continuous
- Drops segments that are fully inside the leading overlap region (basic de-dup)
- Performs a simple text boundary de-dup based on suffix/prefix matching

Limitations:
- This is a heuristic. It does not do full forced alignment or speaker-aware merging.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class MergedTranscript:
    text: str
    segments: List[Dict[str, Any]]


def _normalize_text(s: str) -> str:
    return " ".join((s or "").split())


def dedupe_text_boundary(prev: str, nxt: str, max_window: int = 1000) -> str:
    """Append nxt to prev with simple overlap de-dup.

    Finds the longest suffix of prev that matches a prefix of nxt and removes it from nxt.
    Increased max_window to 1000 for better de-dup when segments are unavailable.
    """

    if not prev:
        return nxt or ""
    if not nxt:
        return prev

    prev_n = _normalize_text(prev)
    nxt_n = _normalize_text(nxt)

    # Work on normalized variants for matching, but apply cut on original 'nxt' length
    # using a best-effort approach.
    max_len = min(len(prev_n), len(nxt_n), max_window)

    best = 0
    for k in range(1, max_len + 1):
        if prev_n[-k:] == nxt_n[:k]:
            best = k

    if best <= 0:
        return prev + "\n\n" + nxt

    # Cut roughly corresponding prefix from original 'nxt'.
    # We re-normalize the original nxt and then take the remaining tail.
    # This keeps behavior stable for sentence-level overlaps.
    remainder = nxt_n[best:].lstrip()
    if not remainder:
        return prev

    return prev + "\n\n" + remainder


def merge_chunk_segments(
    chunk_segments: Sequence[Dict[str, Any]],
    start_offset_sec: float,
    *,
    drop_leading_overlap_sec: float = 0.0,
) -> List[Dict[str, Any]]:
    """Apply time offset and drop segments in the leading overlap region."""

    merged: List[Dict[str, Any]] = []

    for seg in chunk_segments or []:
        # Accept both dict-like and object-like inputs
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        text = seg.get("text") or seg.get("transcript") or ""

        # Drop segments that are fully inside the overlap region (for non-first chunks)
        if drop_leading_overlap_sec > 0 and end <= float(drop_leading_overlap_sec) + 1e-6:
            continue

        start_ts = round(start + float(start_offset_sec), 3)
        end_ts = round(end + float(start_offset_sec), 3)
        if end_ts < start_ts:
            end_ts = start_ts

        merged.append({"start": start_ts, "end": end_ts, "text": text})

    # Ensure monotonic ordering
    merged.sort(key=lambda s: (s["start"], s["end"]))
    return merged


def merge_transcripts(
    chunks: Sequence[Tuple[str, Optional[Sequence[Dict[str, Any]]], float]],
    *,
    overlap_sec: float = 0.8,
) -> MergedTranscript:
    """Merge chunk texts and segments.

    Args:
        chunks: sequence of (text, segments, chunk_start_offset_sec)
        overlap_sec: configured overlap (used for de-dup at the start of each chunk after the first)
    """

    merged_text = ""
    merged_segments: List[Dict[str, Any]] = []

    for idx, (text, segments, offset) in enumerate(chunks):
        # Fallback deduplication when segments are unavailable:
        # Drop first ~200 chars from non-first chunks (heuristic for leading overlap).
        chunk_text = text or ""
        if idx > 0 and (not segments or len(segments) == 0) and len(chunk_text) > 200:
            # Heuristically drop the first ~200 chars (overlap zone)
            chunk_text = chunk_text[200:].lstrip()

        merged_text = dedupe_text_boundary(merged_text, chunk_text) if merged_text else chunk_text

        if segments is None:
            continue

        merged_segments.extend(
            merge_chunk_segments(
                list(segments),
                start_offset_sec=float(offset),
                drop_leading_overlap_sec=(float(overlap_sec) if idx > 0 else 0.0),
            )
        )

    return MergedTranscript(text=merged_text.strip(), segments=merged_segments)
