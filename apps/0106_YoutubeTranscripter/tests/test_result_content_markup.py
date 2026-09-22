"""Focused tests for persisted result markup and request validation."""

from pathlib import Path
import sys

import pytest


APP_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(APP_ROOT / "backend"))

from routers.schemas import UpdateResultContentRequest  # noqa: E402
from services.rich_text import to_plain_text  # noqa: E402


@pytest.mark.parametrize(
    ("formatted", "plain"),
    [
        ("**太字** と ==重要==", "太字 と 重要"),
        ("==**重なった装飾**==", "重なった装飾"),
        ("改行\nも保持", "改行\nも保持"),
    ],
)
def test_to_plain_text_removes_only_supported_markers(formatted, plain):
    assert to_plain_text(formatted) == plain


def test_update_request_accepts_documented_content_type():
    request = UpdateResultContentRequest(
        content_type="qa_answer",
        content="**回答**",
        qa_id="qa-1",
    )
    assert request.content_type == "qa_answer"
    assert request.qa_id == "qa-1"


def test_update_request_rejects_unknown_content_type():
    with pytest.raises(ValueError):
        UpdateResultContentRequest(content_type="arbitrary_field", content="x")
