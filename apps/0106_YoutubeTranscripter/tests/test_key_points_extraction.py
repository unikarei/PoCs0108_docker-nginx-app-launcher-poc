"""Focused tests for detailed key-point extraction and Results tab wiring."""

from pathlib import Path
import importlib
import sys
from types import SimpleNamespace


APP_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = APP_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def test_default_prompt_and_gpt5_request_omit_temperature(monkeypatch):
    calls = []

    class FakeCompletions:
        def create(self, **options):
            calls.append(options)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="### 1. 章\n- 要点"))])

    class FakeOpenAI:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    sys.modules.pop("services.key_points_service", None)
    service = importlib.import_module("services.key_points_service")

    result = service.KeyPointsService(api_key="test-key").extract(
        "Transcript text",
        service.DEFAULT_KEY_POINTS_PROMPT,
        "gpt-5-mini",
    )

    assert result.success is True
    assert "詳細要点抽出プロンプト" in service.DEFAULT_KEY_POINTS_PROMPT
    assert calls[0]["model"] == "gpt-5-mini"
    assert "temperature" not in calls[0]
    assert calls[0]["messages"][1]["content"].endswith("Transcript text")


def test_results_tab_removes_proofread_tab_and_keeps_key_points():
    source = (APP_ROOT / "frontend" / "src" / "components" / "tabs" / "ResultsTab.tsx").read_text(
        encoding="utf-8"
    )

    assert "setActive('proofread')" not in source
    assert "active === 'proofread'" not in source
    assert "type SubTab = 'youtube-transcript' | 'transcript' | 'key-points' | 'qa' | 'note'" in source
    assert "requestKeyPoints" in source
    assert "要点抽出プロンプト編集" in source
    assert "key_points_summary" in source
    assert "const hasNoLocalEdits" in source
    assert "nextDrafts[key] = value" in source
    assert "nextSavedDrafts[key] = value" in source
    assert "pollForAutomaticProofread" in source

    page_source = (APP_ROOT / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
    library_source = (APP_ROOT / "frontend" / "src" / "components" / "tabs" / "LibraryTab.tsx").read_text(
        encoding="utf-8"
    )
    assert "libraryFolderId" in page_source
    assert "selectedFolderId={libraryFolderId}" in page_source
    assert "onSelectedFolderChange={setLibraryFolderId}" in page_source
    assert "preferredFolderId" in library_source
    assert "Restore the last folder" in library_source

    editor_source = (APP_ROOT / "frontend" / "src" / "components" / "RichTextEditor.tsx").read_text(
        encoding="utf-8"
    )
    assert "document.createElement('mark')" in editor_source
    assert "mark.dataset.noteFormat = 'highlight'" in editor_source
    assert "range.extractContents()" in editor_source

    jobs_source = (BACKEND_ROOT / "routers" / "jobs.py").read_text(encoding="utf-8")
    schemas_source = (BACKEND_ROOT / "routers" / "schemas.py").read_text(encoding="utf-8")
    worker_source = (BACKEND_ROOT / "worker.py").read_text(encoding="utf-8")
    manager_source = (BACKEND_ROOT / "services" / "job_manager.py").read_text(encoding="utf-8")

    assert '"/{job_id}/key-points"' in jobs_source
    assert "KeyPointsRequest" in schemas_source
    assert "key_points_summary" in jobs_source
    assert "job.transcript.text" in worker_source
    assert "_queue_automatic_proofread" in worker_source
    assert "args=[job.id, request.proofread_model]" in jobs_source
    assert "proofread_model: str = Field(default=\"gpt-4o-mini\"" in schemas_source
    assert '"error"' in worker_source
    assert "upsert_key_points_summary" in manager_source
