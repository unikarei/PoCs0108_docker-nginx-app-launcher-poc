"""Manage registered Docker applications through a safe host-side API.

The Manager API is the project's control plane. It stores registrations in
``config/apps.json``, generates the Compose and Nginx files from those records,
and invokes only fixed Docker Compose operations. The Launcher calls this HTTP
API; it never receives Docker socket access or arbitrary command execution.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "apps.json"
GENERATED_DIR = REPO_ROOT / "generated"
COMPOSE_OVERRIDE_PATH = GENERATED_DIR / "docker-compose.apps.yml"
NGINX_GENERATED_PATH = GENERATED_DIR / "nginx.conf"
ALLOWED_APPS = ("app1", "app2", "app3", "app4")
APP_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
COMMAND_TIMEOUT_SECONDS = 60
logger = logging.getLogger("manager-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Manager API")


class AppRegistration(BaseModel):
    """Persisted application metadata shared by CRUD and generated files."""

    display_name: str = Field(min_length=1, max_length=120)
    app_id: str = Field(min_length=1, max_length=63)
    source_directory: str
    route_path: str = ""
    internal_port: int = Field(default=8000, ge=1, le=65535)
    health_path: str = "/health"
    dockerfile: str = "Dockerfile"
    deployment_type: Literal["single", "bundle"] = "single"
    compose_file: str = ""
    public_service: str = ""
    enabled: bool = True
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    @field_validator("app_id")
    @classmethod
    def validate_app_id(cls, value: str) -> str:
        if not APP_ID_PATTERN.fullmatch(value):
            raise ValueError("app_id must contain only lowercase letters, digits, and hyphens")
        return value

    @field_validator("route_path")
    @classmethod
    def validate_route_path(cls, value: str) -> str:
        if value == "":
            return ""
        if not value.startswith("/") or ".." in value or "?" in value or "#" in value:
            raise ValueError("route_path must be an absolute URL path without traversal")
        return "/" + value.strip("/") + "/" if value != "/" else "/"

    @field_validator("health_path")
    @classmethod
    def validate_health_path(cls, value: str) -> str:
        if not value.startswith("/") or ".." in value:
            raise ValueError("health_path must be a safe absolute path")
        return value

    @model_validator(mode="after")
    def validate_deployment_fields(self) -> "AppRegistration":
        """Require Compose metadata only for a multi-service bundle registration."""
        if self.deployment_type == "bundle" and (not self.compose_file or not self.public_service):
            raise ValueError("bundle registrations require compose_file and public_service")
        return self


class AppCreate(AppRegistration):
    """Input model for adding an application."""


class AppUpdate(BaseModel):
    """Editable fields; app_id is intentionally immutable."""

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    source_directory: str | None = None
    route_path: str | None = None
    internal_port: int | None = Field(default=None, ge=1, le=65535)
    health_path: str | None = None
    dockerfile: str | None = None
    deployment_type: Literal["single", "bundle"] | None = None
    compose_file: str | None = None
    public_service: str | None = None
    enabled: bool | None = None
    description: str | None = None


class RemoveRequest(BaseModel):
    """Removal confirmation; source removal is opt-in and uses safe trash move."""

    remove_source: bool = False
    confirm_app_id: str


def _now() -> str:
    """Return the current UTC time in portable ISO-8601 form for registry metadata."""
    return datetime.now(timezone.utc).isoformat()


def _default_apps() -> list[dict[str, Any]]:
    """Create the initial sample registrations when no registry exists yet."""
    return [
        {
            "display_name": name.upper(), "app_id": name, "source_directory": f"apps/{name}",
            "route_path": f"/{name}/", "internal_port": 8000, "health_path": "/health",
            "dockerfile": "Dockerfile", "enabled": True, "description": "Initial PoC app",
            "created_at": _now(), "updated_at": _now(),
        }
        for name in ALLOWED_APPS
    ]


def _read_apps() -> list[dict[str, Any]]:
    """Load the registry, initializing it with samples on its first use."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        _atomic_write(_default_apps())
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _atomic_write(records: list[dict[str, Any]]) -> None:
    """Replace the registry atomically so readers never see partially written JSON."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=CONFIG_DIR, delete=False) as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(CONFIG_PATH)


def _find(app_id: str) -> dict[str, Any]:
    """Find one registered app or return a clear HTTP 404 error."""
    record = next((item for item in _read_apps() if item["app_id"] == app_id), None)
    if record is None:
        raise HTTPException(404, f"Unknown app_id: {app_id}")
    return record


def _safe_path(value: str, *, must_exist: bool = True) -> Path:
    """Resolve a path only when it remains inside this project directory."""
    candidate = (REPO_ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(400, "source_directory must remain inside the project") from exc
    if must_exist and not candidate.exists():
        raise HTTPException(400, f"Path does not exist: {value}")
    return candidate


def _safe_source_for_delete(value: str) -> Path:
    """削除対象をapps配下の実ディレクトリに限定する。"""
    candidate = _safe_path(value)
    apps_root = (REPO_ROOT / "apps").resolve()
    try:
        candidate.relative_to(apps_root)
    except ValueError as exc:
        raise HTTPException(400, "Source deletion is allowed only below the apps directory") from exc
    if candidate == apps_root or candidate.is_symlink() or not candidate.is_dir():
        raise HTTPException(400, "Unsafe source directory")
    return candidate


def _validate_files(record: dict[str, Any]) -> None:
    """Validate either a single Dockerfile app or a safe local Compose bundle."""
    if record.get("deployment_type", "single") == "bundle":
        _validate_bundle(record)
        return
    source = _safe_path(record["source_directory"])
    dockerfile = (source / record["dockerfile"]).resolve()
    try:
        dockerfile.relative_to(source)
    except ValueError as exc:
        raise HTTPException(400, "dockerfile must remain inside source_directory") from exc
    if not dockerfile.is_file():
        raise HTTPException(400, f"Dockerfile does not exist: {dockerfile}")


def _bundle_path(source: Path, value: str, label: str) -> Path:
    """Resolve a bundle path only when it remains below the selected source directory."""
    candidate = (source / value).resolve()
    try:
        candidate.relative_to(source)
    except ValueError as exc:
        raise HTTPException(400, f"{label} must remain inside source_directory") from exc
    return candidate


def _rewrite_bundle_service_refs(value: Any, names: dict[str, str]) -> Any:
    """Rewrite URL-style references to source service names after namespacing."""
    if isinstance(value, str):
        for original, generated in names.items():
            value = re.sub(rf"(?<=[/@]){re.escape(original)}(?=[:/])", generated, value)
        return value
    if isinstance(value, list):
        return [_rewrite_bundle_service_refs(item, names) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_bundle_service_refs(item, names) for key, item in value.items()}
    return value


def _validate_bundle_build(source: Path, service_name: str, build: Any) -> None:
    """Ensure each build context and Dockerfile remains within the bundle source."""
    if isinstance(build, str):
        _bundle_path(source, build, f"services.{service_name}.build")
        return
    if not isinstance(build, dict):
        raise HTTPException(400, f"services.{service_name}.build must be a string or mapping")
    context = _bundle_path(source, str(build.get("context", ".")), f"services.{service_name}.build.context")
    if "dockerfile" in build:
        dockerfile = (context / str(build["dockerfile"])).resolve()
        try:
            dockerfile.relative_to(context)
        except ValueError as exc:
            raise HTTPException(400, f"services.{service_name}.build.dockerfile must remain inside build context") from exc


def _validate_bundle_volumes(source: Path, service_name: str, volumes: Any) -> None:
    """Allow named volumes and source-local binds while rejecting Docker socket mounts."""
    if volumes is None:
        return
    if not isinstance(volumes, list):
        raise HTTPException(400, f"services.{service_name}.volumes must be a list")
    for volume in volumes:
        if isinstance(volume, str):
            host_path = volume.split(":", 1)[0]
            if host_path == "/var/run/docker.sock":
                raise HTTPException(400, "Docker socket mounts are not allowed")
            if host_path.startswith(".") or Path(host_path).is_absolute():
                _bundle_path(source, host_path, f"services.{service_name}.volumes")
        elif isinstance(volume, dict) and volume.get("type") == "bind":
            host_path = str(volume.get("source", ""))
            if host_path == "/var/run/docker.sock":
                raise HTTPException(400, "Docker socket mounts are not allowed")
            _bundle_path(source, host_path, f"services.{service_name}.volumes.source")
        elif not isinstance(volume, dict):
            raise HTTPException(400, f"services.{service_name}.volumes has an invalid entry")


def _validate_bundle(record: dict[str, Any]) -> None:
    """Parse and reject unsafe Compose features before registering a bundle."""
    source = _safe_path(record["source_directory"])
    compose_path = _bundle_path(source, record["compose_file"], "compose_file")
    if not compose_path.is_file():
        raise HTTPException(400, f"Compose file does not exist: {compose_path}")
    try:
        document = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"Compose file is invalid YAML: {exc}") from exc
    services = document.get("services") if isinstance(document, dict) else None
    if not isinstance(services, dict) or not services:
        raise HTTPException(400, "Compose bundle must define services")
    if record["public_service"] not in services:
        raise HTTPException(400, "public_service must name a service in the Compose bundle")
    for service_name, service in services.items():
        if not isinstance(service, dict):
            raise HTTPException(400, f"services.{service_name} must be a mapping")
        if service.get("ports"):
            raise HTTPException(400, "Bundle services must not publish host ports")
        if service.get("network_mode") == "host":
            raise HTTPException(400, "Host networking is not allowed")
        if service.get("privileged") is True:
            raise HTTPException(400, "Privileged containers are not allowed")
        if "build" in service:
            _validate_bundle_build(source, service_name, service["build"])
        _validate_bundle_volumes(source, service_name, service.get("volumes"))


def _validate_unique(records: list[dict[str, Any]], current_id: str | None = None) -> None:
    """Reject duplicate application IDs and duplicate browser routes."""
    ids = [item["app_id"] for item in records if item["app_id"] != current_id]
    routes = [item["route_path"] for item in records if item["app_id"] != current_id]
    if len(ids) != len(set(ids)):
        raise HTTPException(409, "app_id already exists")
    if len(routes) != len(set(routes)):
        raise HTTPException(409, "route_path already exists")


def _compose_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a fixed Compose argument list and report command failures as HTTP errors."""
    command = ["docker", "compose", "-f", "docker-compose.yml", "-f", str(COMPOSE_OVERRIDE_PATH), *args]
    logger.info("running command: %s", " ".join(command))
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True,
                                timeout=COMMAND_TIMEOUT_SECONDS, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(504, f"Docker command unavailable or timed out: {exc}") from exc
    if result.returncode:
        raise HTTPException(500, {"message": "Docker command failed", "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]})
    return result


# Gateway refresh block: make generated Nginx routes active in the running container.
def _refresh_nginx() -> None:
    """Recreate Nginx so it reads the latest generated route configuration."""
    _compose_command(["up", "-d", "--force-recreate", "nginx"])


# Configuration-generation block: write the Compose and Nginx artifacts from registrations.
def _bundle_generated_parts(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Return namespaced services, volumes, and the public service for one safe bundle."""
    source = _safe_path(record["source_directory"])
    compose_path = _bundle_path(source, record["compose_file"], "compose_file")
    document = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    original_services = document["services"]
    names = {name: f"{record['app_id']}-{name}" for name in original_services}
    volume_names = {name: f"{record['app_id']}-{name}" for name in (document.get("volumes") or {})}
    generated: dict[str, Any] = {}
    for original_name, original_service in original_services.items():
        service = deepcopy(original_service)
        if "build" in service:
            build = service["build"]
            if isinstance(build, str):
                service["build"] = {"context": f"{record['source_directory']}/{build}"}
            else:
                build["context"] = f"{record['source_directory']}/{build.get('context', '.')}"
        if isinstance(service.get("env_file"), str):
            service["env_file"] = f"{record['source_directory']}/{service['env_file']}"
        elif isinstance(service.get("env_file"), list):
            service["env_file"] = [f"{record['source_directory']}/{path}" for path in service["env_file"]]
        if isinstance(service.get("depends_on"), list):
            service["depends_on"] = [names.get(name, name) for name in service["depends_on"]]
        elif isinstance(service.get("depends_on"), dict):
            service["depends_on"] = {names.get(name, name): value for name, value in service["depends_on"].items()}
        if isinstance(service.get("volumes"), list):
            service["volumes"] = [
                f"{volume_names.get(entry.split(':', 1)[0], entry.split(':', 1)[0])}:{entry.split(':', 1)[1]}"
                if isinstance(entry, str) and ":" in entry and entry.split(":", 1)[0] in volume_names else entry
                for entry in service["volumes"]
            ]
        service = _rewrite_bundle_service_refs(service, names)
        service.pop("ports", None)
        service["networks"] = ["multiapp_net"]
        generated[names[original_name]] = service
    volumes = {volume_names[name]: value for name, value in (document.get("volumes") or {}).items()}
    return generated, volumes, names[record["public_service"]]


def _managed_service_names(record: dict[str, Any]) -> list[str]:
    """Return every generated Compose service controlled by one registration."""
    if record.get("deployment_type", "single") == "bundle":
        services, _, _ = _bundle_generated_parts(record)
        return list(services)
    return [record["app_id"]]


def _generate() -> None:
    """Generate all app service and Nginx route definitions from enabled records."""
    records = _read_apps()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    services: dict[str, Any] = {}
    volumes: dict[str, Any] = {}
    routes: list[str] = ["    resolver 127.0.0.11 ipv6=off valid=10s;\n    location /launcher/ {\n        proxy_pass http://launcher:8000/;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }"]
    for item in records:
        if not item["enabled"]:
            continue
        is_bundle = item.get("deployment_type", "single") == "bundle"
        if is_bundle:
            bundle_services, bundle_volumes, upstream = _bundle_generated_parts(item)
            services.update(bundle_services)
            volumes.update(bundle_volumes)
        else:
            source = Path(item["source_directory"]).as_posix()
            upstream = item["app_id"]
            services[item["app_id"]] = {
                "build": {"context": source, "dockerfile": item["dockerfile"]},
                "expose": [str(item["internal_port"])], "networks": ["multiapp_net"],
                "healthcheck": {"test": ["CMD", "python", "-c", f"import urllib.request; urllib.request.urlopen('http://127.0.0.1:{item['internal_port']}{item['health_path']}', timeout=3)"], "interval": "10s", "timeout": "5s", "retries": 5, "start_period": "5s"},
            }
        if is_bundle:
            api_route = f"{item['route_path']}api-proxy/"
            routes.append(f"    location {api_route} {{\n        set $app_upstream {upstream}:{item['internal_port']};\n        proxy_pass http://$app_upstream;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }}")
            routes.append(f"    location {item['route_path']} {{\n        set $app_upstream {upstream}:{item['internal_port']};\n        rewrite ^{item['route_path']}(.*)$ /$1 break;\n        proxy_pass http://$app_upstream;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }}")
        else:
            routes.append(f"    location {item['route_path']} {{\n        set $app_upstream {upstream}:{item['internal_port']};\n        proxy_pass http://$app_upstream/;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }}")
    compose = "# AUTO-GENERATED; DO NOT EDIT.\n" + yaml.safe_dump(
        {"services": services, **({"volumes": volumes} if volumes else {})}, sort_keys=False, allow_unicode=True
    )
    COMPOSE_OVERRIDE_PATH.write_text(compose, encoding="utf-8")
    nginx = "# AUTO-GENERATED; DO NOT EDIT.\nserver {\n    listen 80;\n    server_name _;\n    location = / { return 302 /launcher/; }\n" + "\n".join(routes) + "\n}\n"
    NGINX_GENERATED_PATH.write_text(nginx, encoding="utf-8")
    _refresh_nginx()


@app.get("/health")
def health() -> dict[str, str]:
    """Provide a lightweight liveness check for scripts and operators."""
    return {"status": "ok", "app": "manager-api"}


@app.get("/api/apps")
def list_apps() -> dict[str, list[dict[str, Any]]]:
    """Return all stored registrations for the Launcher interface."""
    return {"apps": _read_apps()}


def _status_map() -> dict[str, str]:
    """Composeの状態を登録アプリごとの辞書へ変換する。"""
    result = _compose_command(["ps", "--format", "{{.Service}}|{{.State}}"])
    statuses = {item["app_id"]: "unknown" for item in _read_apps()}
    service_to_app = {
        service: item["app_id"] for item in _read_apps() for service in _managed_service_names(item)
    }
    for line in result.stdout.splitlines():
        if "|" in line:
            service, state = line.split("|", 1)
            app_id = service_to_app.get(service.strip())
            if app_id:
                statuses[app_id] = state.strip().lower()
    return statuses


@app.get("/api/status")
def legacy_status() -> dict[str, dict[str, str]]:
    """既存Launcher向けの状態APIを維持する。"""
    return {"status": _status_map()}


@app.get("/api/status/{app_name}")
def legacy_status_single(app_name: str) -> dict[str, str]:
    """Return the Compose state of one registered app."""
    _find(app_name)
    return {"app": app_name, "status": _status_map().get(app_name, "unknown")}


@app.post("/api/start/{app_name}")
def legacy_start(app_name: str) -> dict[str, str]:
    """Start one app through the backward-compatible endpoint."""
    return _lifecycle(app_name, "start")


@app.post("/api/stop/{app_name}")
def legacy_stop(app_name: str) -> dict[str, str]:
    """Stop one app through the backward-compatible endpoint."""
    return _lifecycle(app_name, "stop")


@app.get("/api/apps/{app_id}")
def inspect_app(app_id: str) -> dict[str, Any]:
    """Return the full persisted configuration for a selected app."""
    return _find(app_id)


@app.get("/api/directories")
def list_directories() -> dict[str, list[str]]:
    """アプリ配置候補をプロジェクト内の相対パスで返す。"""
    directories: list[str] = ['.']                                      # Include the project root in the tree.
    for root in (REPO_ROOT / "apps",):
        if not root.exists():                                           # Check whether the app storage exists.
            continue                                                    # Skip missing storage safely.
        directories.append('apps')                                      # Make the storage folder selectable.
        for path in sorted(root.rglob("*")):
            if not path.is_dir() or any(part in {".git", ".venv", "__pycache__", "node_modules"} for part in path.parts):
                continue
            directories.append(path.relative_to(REPO_ROOT).as_posix())
    return {"directories": directories}


@app.post("/api/apps")
def add_app(payload: AppCreate) -> dict[str, Any]:
    """Validate, persist, and generate routing for a new application."""
    records = _read_apps()
    data = payload.model_dump()
    data["route_path"] = data["route_path"] or f"/{data['app_id']}/"
    data["created_at"] = data["updated_at"] = _now()
    _validate_files(data)
    _validate_unique(records + [data])
    records.append(data)
    _atomic_write(records)
    _generate()
    return data


@app.patch("/api/apps/{app_id}")
def update_app(app_id: str, payload: AppUpdate) -> dict[str, Any]:
    """Validate and save permitted edits without changing the app identifier."""
    records = _read_apps()
    current = _find(app_id)
    changes = payload.model_dump(exclude_none=True)
    current.update(changes)
    current["updated_at"] = _now()
    _validate_files(current)
    _validate_unique(records, current_id=app_id)
    _atomic_write(records)
    _generate()
    return current


@app.delete("/api/apps/{app_id}")
def remove_app(app_id: str, payload: RemoveRequest) -> dict[str, str]:
    """Remove a registration and optionally remove its safely-scoped source folder."""
    if payload.confirm_app_id != app_id:
        raise HTTPException(400, "confirm_app_id does not match")
    records = _read_apps()
    target = _find(app_id)
    _compose_command(["stop", *_managed_service_names(target)])
    _atomic_write([item for item in records if item["app_id"] != app_id])
    _generate()
    if payload.remove_source:
        source = _safe_source_for_delete(target["source_directory"])
        shutil.rmtree(source)
        return {"status": "success", "message": f"{app_id} and its source directory were deleted"}
    return {"status": "success", "message": f"{app_id} removed; source directory was preserved"}


def _lifecycle(app_id: str, operation: Literal["start", "stop", "restart", "rebuild"]) -> dict[str, str]:
    """Execute one explicitly allowed Docker lifecycle action for a registered app."""
    record = _find(app_id)
    services = _managed_service_names(record)
    args = ["up", "-d", "--build", *services] if operation == "start" else [operation, *services]
    if operation == "rebuild":
        args = ["build", *services]
    _compose_command(args)
    return {"status": "success", "message": f"{app_id} {operation} completed"}


@app.post("/api/apps/{app_id}/{operation}")
def lifecycle(app_id: str, operation: Literal["start", "stop", "restart", "rebuild"]) -> dict[str, str]:
    """Expose the controlled lifecycle helper as an HTTP endpoint."""
    return _lifecycle(app_id, operation)


@app.get("/api/apps/{app_id}/logs")
def logs(app_id: str, lines: int = 100) -> dict[str, str]:
    """Return a size-limited tail of one app's Docker Compose logs."""
    record = _find(app_id)
    result = _compose_command(["logs", "--no-color", "--tail", str(max(1, min(lines, 100))), *_managed_service_names(record)])
    return {"app_id": app_id, "logs": result.stdout[-20000:]}


@app.post("/api/generate")
def generate() -> dict[str, str]:
    """Regenerate derived Compose and Nginx configuration from the registry."""
    _generate()
    return {"status": "success", "message": "Compose and Nginx files generated"}
