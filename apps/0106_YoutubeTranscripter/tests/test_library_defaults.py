"""Focused tests for Library folder order and generated job titles."""

from datetime import datetime
from pathlib import Path
import sys


APP_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = APP_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def test_default_title_uses_uploader_and_unpadded_date():
    from services.job_title import build_default_job_title

    created_at = datetime(2026, 9, 22, 8, 30)
    assert build_default_job_title({"uploader": "配信者A"}, created_at) == "【配信者A】YouTube 2026/9/22"
    assert build_default_job_title({}, created_at) == "【YouTube】YouTube 2026/9/22"


def test_folder_tree_explicitly_prioritizes_inbox():
    source = (BACKEND_ROOT / "routers" / "folders.py").read_text(encoding="utf-8")

    assert "def _folder_sort_key" in source
    assert 'name.casefold() == "inbox"' in source
    assert "siblings = sorted(" in source
