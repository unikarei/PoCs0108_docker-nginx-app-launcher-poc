"""Helpers for the small, safe result-text markup used by the UI."""

import re


_MARKUP_TOKEN_RE = re.compile(r"\*\*|==")


def to_plain_text(value: str | None) -> str:
    """Remove supported formatting markers before semantic text processing."""
    if not value:
        return ""
    return _MARKUP_TOKEN_RE.sub("", value)
