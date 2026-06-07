from pathlib import Path
import subprocess
import logging

from fastapi import FastAPI, HTTPException

ALLOWED_APPS = ("app1", "app2", "app3", "app4")
COMMAND_TIMEOUT_SECONDS = 15

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("manager-api")

# Resolve repository root regardless of where uvicorn is started from.
REPO_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Manager API")


def _validate_app_name(app_name: str) -> None:
    if app_name not in ALLOWED_APPS:
        raise HTTPException(status_code=400, detail=f"Unsupported app name: {app_name}")


def _run_compose_command(command_args: list[str]) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", *command_args]
    logger.info("running command: %s", " ".join(command))
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="docker command is not available") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"Command timeout: {' '.join(command)}") from exc

    if result.returncode != 0:
        detail = {
            "message": f"Command failed: {' '.join(command)}",
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        raise HTTPException(status_code=500, detail=detail)

    return result


def _collect_status() -> dict[str, str]:
    status_map = {app_name: "unknown" for app_name in ALLOWED_APPS}
    result = _run_compose_command(["ps", "--format", "{{.Service}}|{{.State}}"])

    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        service_name, state_text = line.split("|", 1)
        service_name = service_name.strip()
        if service_name in status_map:
            status_map[service_name] = state_text.strip().lower()

    return status_map


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "manager-api"}


@app.get("/api/status")
def api_status() -> dict[str, dict[str, str]]:
    return {"status": _collect_status()}


@app.get("/api/status/{app_name}")
def api_status_single(app_name: str) -> dict[str, str]:
    _validate_app_name(app_name)
    status_map = _collect_status()
    return {"app": app_name, "status": status_map[app_name]}


@app.post("/api/start/{app_name}")
def api_start(app_name: str) -> dict[str, str]:
    _validate_app_name(app_name)
    _run_compose_command(["start", app_name])
    logger.info("started service: %s", app_name)
    return {"status": "success", "message": f"{app_name} started."}


@app.post("/api/stop/{app_name}")
def api_stop(app_name: str) -> dict[str, str]:
    _validate_app_name(app_name)
    _run_compose_command(["stop", app_name])
    logger.info("stopped service: %s", app_name)
    return {"status": "success", "message": f"{app_name} stopped."}
