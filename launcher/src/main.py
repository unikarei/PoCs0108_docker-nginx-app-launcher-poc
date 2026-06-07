import os
import base64
import logging
import secrets

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

ALLOWED_APPS = ["app1", "app2", "app3", "app4"]
MANAGER_API_BASE_URL = os.getenv("MANAGER_API_BASE_URL", "http://host.docker.internal:9000")
REQUEST_TIMEOUT_SECONDS = 10.0
LAUNCHER_BASIC_AUTH_USER = os.getenv("LAUNCHER_BASIC_AUTH_USER", "launcher")
LAUNCHER_BASIC_AUTH_PASSWORD = os.getenv("LAUNCHER_BASIC_AUTH_PASSWORD", "launcher-pass")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("launcher")

app = FastAPI(title="Launcher")

HOME_PAGE_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Launcher</title>
    <style>
      body { font-family: sans-serif; margin: 2rem; }
      table { border-collapse: collapse; width: 100%; max-width: 900px; }
      th, td { border: 1px solid #ddd; padding: 0.6rem; text-align: left; }
      th { background: #f6f6f6; }
      .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
      button, a { padding: 0.35rem 0.65rem; }
      #message { margin-top: 1rem; min-height: 1.5rem; }
    </style>
  </head>
  <body>
    <main>
      <h1>Launcher</h1>
      <p>Manage app1, app2, app3 and app4 from this page.</p>

      <table>
        <thead>
          <tr>
            <th>App</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id=\"apps-body\"></tbody>
      </table>

      <p id=\"message\"></p>
    </main>

    <script>
      const APPS = ['app1', 'app2', 'app3', 'app4'];
      const tbody = document.getElementById('apps-body');
      const message = document.getElementById('message');

      function setMessage(text) {
        message.textContent = text;
      }

      function rowHtml(appName, statusText) {
        return `
          <tr data-app="${appName}">
            <td>${appName}</td>
            <td class="status">${statusText}</td>
            <td>
              <div class="actions">
                <a href="../${appName}/" target="_blank" rel="noopener">Open</a>
                <button data-action="start" data-app="${appName}">Start</button>
                <button data-action="stop" data-app="${appName}">Stop</button>
              </div>
            </td>
          </tr>
        `;
      }

      async function refreshStatus() {
        try {
          const response = await fetch('./api/status');
          const payload = await response.json();
          const statusMap = payload.status || {};

          tbody.innerHTML = APPS.map((app) => rowHtml(app, statusMap[app] || 'unknown')).join('');
          bindActionButtons();
          setMessage('Status updated.');
        } catch (error) {
          setMessage('Failed to fetch status.');
        }
      }

      async function callAction(action, appName) {
        try {
          setMessage(`${action} ${appName}...`);
          const response = await fetch(`./api/${action}/${appName}`, { method: 'POST' });
          const payload = await response.json();

          if (!response.ok) {
            throw new Error(payload.detail || 'Request failed');
          }

          setMessage(payload.message || `${action} ${appName} done.`);
          await refreshStatus();
        } catch (error) {
          setMessage(error.message || 'Action failed.');
        }
      }

      function bindActionButtons() {
        const buttons = document.querySelectorAll('button[data-action]');
        buttons.forEach((button) => {
          button.addEventListener('click', async () => {
            const action = button.dataset.action;
            const appName = button.dataset.app;
            await callAction(action, appName);
          });
        });
      }

      refreshStatus();
    </script>
  </body>
</html>
"""


def _validate_app_name(app_name: str) -> None:
    if app_name not in ALLOWED_APPS:
        raise HTTPException(status_code=400, detail=f"Unsupported app name: {app_name}")


def _check_basic_auth(request: Request) -> None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        encoded = auth_header.split(" ", 1)[1].strip()
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication header",
            headers={"WWW-Authenticate": "Basic"},
        ) from exc

    valid_user = secrets.compare_digest(username, LAUNCHER_BASIC_AUTH_USER)
    valid_pass = secrets.compare_digest(password, LAUNCHER_BASIC_AUTH_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def _manager_get(path: str) -> dict:
    url = f"{MANAGER_API_BASE_URL}{path}"
    try:
        response = httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


def _manager_post(path: str) -> dict:
    url = f"{MANAGER_API_BASE_URL}{path}"
    try:
        response = httpx.post(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    _check_basic_auth(request)
    return HTMLResponse(content=HOME_PAGE_HTML)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "launcher"}


@app.get("/api/apps")
def api_apps(request: Request) -> dict[str, list[dict[str, str]]]:
    _check_basic_auth(request)
    return {
        "apps": [
            {"name": "app1", "open_path": "/app1/"},
            {"name": "app2", "open_path": "/app2/"},
            {"name": "app3", "open_path": "/app3/"},
            {"name": "app4", "open_path": "/app4/"},
        ]
    }


@app.get("/api/status")
def api_status(request: Request) -> dict:
    _check_basic_auth(request)
    logger.info("status requested")
    return _manager_get("/api/status")


@app.post("/api/start/{app_name}")
def api_start(app_name: str, request: Request) -> dict:
    _check_basic_auth(request)
    _validate_app_name(app_name)
    logger.info("start requested for %s", app_name)
    return _manager_post(f"/api/start/{app_name}")


@app.post("/api/stop/{app_name}")
def api_stop(app_name: str, request: Request) -> dict:
    _check_basic_auth(request)
    _validate_app_name(app_name)
    logger.info("stop requested for %s", app_name)
    return _manager_post(f"/api/stop/{app_name}")
