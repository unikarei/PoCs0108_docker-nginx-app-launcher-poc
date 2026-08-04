"""Docker-free SDD lifecycle tests for the dynamic application registry."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1] / "manager-api"))
from src import main  # noqa: E402


client = TestClient(main.app)


def test_add_rejects_invalid_app_id() -> None:
    response = client.post(
        "/api/apps",
        json={"display_name": "Bad", "app_id": "bad/id", "source_directory": "apps/app1"},
    )
    assert response.status_code == 422


def test_add_validates_and_generates_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    generated: list[bool] = []
    saved: list[list[dict]] = []
    monkeypatch.setattr(main, "_generate", lambda: generated.append(True))
    monkeypatch.setattr(main, "_atomic_write", lambda records: saved.append(records))

    response = client.post(
        "/api/apps",
        json={
            "display_name": "Test application",
            "app_id": "test-application",
            "source_directory": "apps/app1",
            "route_path": "/test-application/",
        },
    )
    assert response.status_code == 200
    assert response.json()["app_id"] == "test-application"
    assert generated and saved


def test_generate_refreshes_nginx_after_writing_routes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Generated routes must be loaded by Nginx before a management operation succeeds."""
    compose_path = tmp_path / "docker-compose.apps.yml"                 # Keep generated Compose isolated.
    nginx_path = tmp_path / "nginx.conf"                                 # Keep generated Nginx isolated.
    refreshed: list[bool] = []                                            # Record the gateway refresh call.
    monkeypatch.setattr(main, "COMPOSE_OVERRIDE_PATH", compose_path)     # Redirect Compose output.
    monkeypatch.setattr(main, "NGINX_GENERATED_PATH", nginx_path)        # Redirect Nginx output.
    monkeypatch.setattr(main, "GENERATED_DIR", tmp_path)                 # Redirect generated directory creation.
    monkeypatch.setattr(main, "_read_apps", lambda: [{                  # Provide one valid generated route.
        "app_id": "app5", "source_directory": "apps/app1", "route_path": "/app5/",
        "internal_port": 8000, "health_path": "/health", "dockerfile": "Dockerfile", "enabled": True,
    }])
    monkeypatch.setattr(main, "_refresh_nginx", lambda: refreshed.append(True))  # Avoid Docker in this unit test.

    main._generate()                                                      # Generate artifacts and request a refresh.

    assert "location /app5/" in nginx_path.read_text(encoding="utf-8")  # Verify the public route is generated.
    assert refreshed == [True]                                            # Verify Nginx is refreshed exactly once.


def test_start_and_stop_use_allowlisted_lifecycle_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(main, "_compose_command", lambda args: commands.append(args))

    assert client.post("/api/apps/app1/start").status_code == 200
    assert client.post("/api/apps/app1/stop").status_code == 200
    assert commands == [["up", "-d", "--build", "app1"], ["stop", "app1"]]


def test_delete_preserves_source_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[list[dict]] = []
    monkeypatch.setattr(main, "_compose_command", lambda args: None)
    monkeypatch.setattr(main, "_generate", lambda: None)
    monkeypatch.setattr(main, "_atomic_write", lambda records: saved.append(records))

    response = client.request(
        "DELETE", "/api/apps/app3", json={"confirm_app_id": "app3", "remove_source": False}
    )
    assert response.status_code == 200
    assert "preserved" in response.json()["message"]
    assert Path("apps/app3").exists()
    assert saved


def test_delete_source_calls_safe_recursive_remove(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    removed: list[Path] = []
    monkeypatch.setattr(main, "_compose_command", lambda args: None)
    monkeypatch.setattr(main, "_generate", lambda: None)
    monkeypatch.setattr(main, "_atomic_write", lambda records: None)
    monkeypatch.setattr(main, "_safe_source_for_delete", lambda value: tmp_path)
    monkeypatch.setattr(main.shutil, "rmtree", lambda path: removed.append(Path(path)))

    response = client.request(
        "DELETE", "/api/apps/app3", json={"confirm_app_id": "app3", "remove_source": True}
    )
    assert response.status_code == 200
    assert removed == [tmp_path]
    assert "source directory were deleted" in response.json()["message"]


def test_delete_source_rejects_project_root() -> None:
    with pytest.raises(Exception):
        main._safe_source_for_delete(".")
