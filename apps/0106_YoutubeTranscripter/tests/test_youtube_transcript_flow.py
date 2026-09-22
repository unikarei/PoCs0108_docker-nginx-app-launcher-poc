"""Unit tests for the YouTube-first transcript retrieval contract."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
from services import youtube_transcript_service as service  # noqa: E402


VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class FakeTrack:
    def __init__(self, language_code, language, is_generated, snippets):
        self.language_code = language_code
        self.language = language
        self.is_generated = is_generated
        self._snippets = snippets

    def fetch(self):
        return self._snippets


class FakeApi:
    tracks = []
    error = None

    def list(self, video_id):
        assert video_id == "dQw4w9WgXcQ"
        if self.error:
            raise self.error
        return self.tracks


def _track(language_code, language, is_generated, text):
    return FakeTrack(
        language_code,
        language,
        is_generated,
        [{"start": 0.0, "duration": 1.5, "text": text}],
    )


def test_manual_track_is_preferred_over_auto_generated(monkeypatch):
    FakeApi.tracks = [
        _track("ja", "Japanese", True, "auto text"),
        _track("en", "English", False, "manual text"),
    ]
    FakeApi.error = None
    monkeypatch.setattr(service, "YouTubeTranscriptApi", FakeApi)

    result = service.retrieve_youtube_transcript(VIDEO_URL, "ja")

    assert result.status == "available"
    assert result.text == "manual text"
    assert result.is_generated is False
    assert len(result.available_tracks) == 2


def test_auto_generated_track_is_used_when_it_is_the_only_track(monkeypatch):
    FakeApi.tracks = [_track("en", "English", True, "auto text")]
    FakeApi.error = None
    monkeypatch.setattr(service, "YouTubeTranscriptApi", FakeApi)

    result = service.retrieve_youtube_transcript(VIDEO_URL, "en")

    assert result.usable
    assert result.is_generated is True
    assert result.language_code == "en"


def test_no_tracks_reports_unavailable(monkeypatch):
    FakeApi.tracks = []
    FakeApi.error = None
    monkeypatch.setattr(service, "YouTubeTranscriptApi", FakeApi)

    result = service.retrieve_youtube_transcript(VIDEO_URL, "ja")

    assert result.status == "unavailable"
    assert result.usable is False
    assert result.error is None


def test_retrieval_error_reports_error_for_audio_fallback(monkeypatch):
    FakeApi.tracks = []
    FakeApi.error = RuntimeError("network unavailable")
    monkeypatch.setattr(service, "YouTubeTranscriptApi", FakeApi)

    result = service.retrieve_youtube_transcript(VIDEO_URL, "ja")

    assert result.status == "error"
    assert result.usable is False
    assert result.error == "YouTube transcript retrieval failed"


def test_selected_track_fetch_error_reports_error(monkeypatch):
    class BrokenTrack(FakeTrack):
        def fetch(self):
            raise RuntimeError("blocked")

    FakeApi.tracks = [BrokenTrack("ja", "Japanese", False, [])]
    FakeApi.error = None
    monkeypatch.setattr(service, "YouTubeTranscriptApi", FakeApi)

    result = service.retrieve_youtube_transcript(VIDEO_URL, "ja")

    assert result.status == "error"
    assert result.video_id == "dQw4w9WgXcQ"


def test_malformed_url_is_safe_error(monkeypatch):
    api_called = False

    def fail_if_called():
        nonlocal api_called
        api_called = True
        return FakeApi()

    monkeypatch.setattr(service, "YouTubeTranscriptApi", fail_if_called)
    result = service.retrieve_youtube_transcript("https://example.com/video", "ja")

    assert result.status == "error"
    assert api_called is False


def test_youtube_success_is_the_no_stt_branch_and_ui_preserves_tab_order():
    worker_source = (Path(__file__).parents[1] / "backend" / "worker.py").read_text(encoding="utf-8")
    results_source = (
        Path(__file__).parents[1] / "frontend" / "src" / "components" / "tabs" / "ResultsTab.tsx"
    ).read_text(encoding="utf-8")

    assert "if youtube_result.usable:" in worker_source
    assert worker_source.index("if youtube_result.usable:") < worker_source.index("audio_extractor = AudioExtractor()")
    assert results_source.index("active === 'youtube-transcript'") < results_source.index("active === 'transcript'")
    assert "type SubTab = 'youtube-transcript' | 'transcript'" in results_source
