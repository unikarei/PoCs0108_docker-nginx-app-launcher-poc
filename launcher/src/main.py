import os                         # 環境変数を読み込む。
import base64                     # Basic認証ヘッダーをデコードする。
import logging                    # 操作履歴を記録する。
import secrets                    # 認証情報を安全に比較する。

import httpx                      # Manager APIへHTTPリクエストを送る。
from fastapi import FastAPI, HTTPException, Request  # API本体とリクエスト型。
from fastapi.responses import HTMLResponse           # HTMLレスポンス型。

# 設定ブロック: 起動時に環境変数を読み、許可範囲とタイムアウトを定める。
ALLOWED_APPS = ["app1", "app2", "app3", "app4"]
MANAGER_API_BASE_URL = os.getenv("MANAGER_API_BASE_URL", "http://host.docker.internal:9000")
REQUEST_TIMEOUT_SECONDS = 10.0
LAUNCHER_BASIC_AUTH_USER = os.getenv("LAUNCHER_BASIC_AUTH_USER", "launcher")
LAUNCHER_BASIC_AUTH_PASSWORD = os.getenv("LAUNCHER_BASIC_AUTH_PASSWORD", "launcher-pass")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")  # ログ形式。
logger = logging.getLogger("launcher")  # Launcher専用ロガーを取得する。

# アプリケーション構築ブロック: Launcher APIを作成する。
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
      <p>Registered applications</p>
      <p><a href="./manage">管理 ⚙</a></p>

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
      let APPS = [];
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
          const [appsResponse, statusResponse] = await Promise.all([fetch('./api/apps'), fetch('./api/status')]);
          const appsPayload = await appsResponse.json();
          const statusPayload = await statusResponse.json();
          APPS = appsPayload.apps || [];
          const statusMap = statusPayload.status || {};

          tbody.innerHTML = APPS.map((item) => rowHtml(item.app_id, statusMap[item.app_id] || 'unknown')).join('');
          bindActionButtons();
          setMessage('Status updated.');
        } catch (error) {
          setMessage('Manager APIに接続できません。');
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

MANAGEMENT_HTML = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>アプリ管理</title>
<style>body{font-family:sans-serif;margin:2rem}input,textarea{display:block;width:100%;max-width:520px;margin:.25rem 0 .75rem;padding:.4rem}button{margin:.2rem;padding:.4rem}.danger{background:#fdd}.card{border:1px solid #ddd;padding:1rem;margin:1rem 0}</style></head>
<body><p><a href="./">← Launcher</a></p><h1>アプリ管理 ⚙</h1><p id="message"></p>
<section class="card"><h2>追加</h2><form id="add-form"><label>表示名<input name="display_name" required></label><label>app_id<input name="app_id" pattern="[a-z0-9-]+" required></label><label>ソースディレクトリ<input name="source_directory" placeholder="apps/my-app" required></label><label>URLパス<input name="route_path" placeholder="/my-app/"></label><label>内部ポート<input name="internal_port" type="number" value="8000" min="1" max="65535"></label><label>ヘルスパス<input name="health_path" value="/health"></label><label>Dockerfile<input name="dockerfile" value="Dockerfile"></label><label>説明<textarea name="description"></textarea></label><button>登録</button></form></section>
<section><h2>登録済みアプリ</h2><div id="apps"></div></section>
<script>
const message=document.getElementById('message'); const apps=document.getElementById('apps');
function say(t){message.textContent=t} function esc(t){return String(t).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
async function load(){const r=await fetch('./api/management/apps');if(!r.ok){say('Manager APIに接続できません');return}const p=await r.json();apps.innerHTML=p.apps.map(a=>`<article class="card"><b>${esc(a.display_name)}</b> (${esc(a.app_id)})<br>URL: ${esc(a.route_path)}<br>ソース: ${esc(a.source_directory)}<br><button onclick="editApp('${a.app_id}','${esc(a.display_name)}','${esc(a.description||'')}')">編集</button><button onclick="action('${a.app_id}','start')">起動</button><button onclick="action('${a.app_id}','stop')">停止</button><button onclick="action('${a.app_id}','restart')">再起動</button><button onclick="action('${a.app_id}','rebuild')">再ビルド</button><button onclick="showLogs('${a.app_id}')">ログ</button><button class="danger" onclick="removeApp('${a.app_id}','${esc(a.display_name)}')">削除</button></article>`).join('')}
async function editApp(id,name,description){const display_name=prompt('表示名',name);if(display_name===null)return;const nextDescription=prompt('説明',description);if(nextDescription===null)return;const r=await fetch('./api/management/apps/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name,description:nextDescription})});const p=await r.json();say(p.message||p.detail||'更新完了');load()}
async function action(id,op){say(op+' '+id+'...');const r=await fetch('./api/management/apps/'+id+'/'+op,{method:'POST'});const p=await r.json();say(p.message||p.detail||'完了');load()}
async function showLogs(id){const r=await fetch('./api/management/apps/'+id+'/logs');const p=await r.json();alert(p.logs||p.detail||'ログなし')}
async function removeApp(id,name){if(!confirm('登録とDockerサービスを削除します。ソースコードは残します。\n'+name+' ('+id+')'))return;const r=await fetch('./api/management/apps/'+id,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_app_id:id,remove_source:false})});const p=await r.json();say(p.message||p.detail||'削除完了');load()}
document.getElementById('add-form').addEventListener('submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));data.internal_port=Number(data.internal_port);const r=await fetch('./api/management/apps',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const p=await r.json();say(p.message||p.detail||'登録完了');if(r.ok)e.target.reset();load()});load();
</script></body></html>"""


# 入力検証ブロック: 操作対象を許可済みアプリに限定する。
def _validate_app_name(app_name: str) -> None:
    """アプリ名が許可リストにあることを確認する。"""
    if app_name not in ALLOWED_APPS:
        raise HTTPException(status_code=400, detail=f"Unsupported app name: {app_name}")


# 認証ブロック: 保護対象エンドポイントのBasic認証を検証する。
def _check_basic_auth(request: Request) -> None:
    """Authorizationヘッダーを検証し、失敗時は401を返す。"""
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


# Manager API連携ブロック: GETで状態情報を取得する。
def _manager_get(path: str) -> dict:
    """Manager APIのGET結果を返す。"""
    url = f"{MANAGER_API_BASE_URL}{path}"
    try:
        response = httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


# Manager API連携ブロック: POSTで開始・停止操作を依頼する。
def _manager_post(path: str) -> dict:
    """Manager APIのPOST結果を返す。"""
    url = f"{MANAGER_API_BASE_URL}{path}"
    try:
        response = httpx.post(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


def _manager_post_json(path: str, payload: dict) -> dict:
    """Manager APIへJSON本文付きPOSTを依頼する。"""
    try:
        response = httpx.post(f"{MANAGER_API_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


def _manager_patch(path: str, payload: dict) -> dict:
    """Manager APIへ更新を依頼する。"""
    try:
        response = httpx.patch(f"{MANAGER_API_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


def _manager_delete(path: str, payload: dict) -> dict:
    """Manager APIへ削除を依頼する。"""
    try:
        response = httpx.delete(f"{MANAGER_API_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Manager API request failed: {exc}") from exc


# 画面エンドポイントブロック: 認証済み利用者へLauncher画面を返す。
@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """LauncherのHTML画面を返す。"""
    _check_basic_auth(request)
    return HTMLResponse(content=HOME_PAGE_HTML)


# ヘルスチェックエンドポイントブロック。
@app.get("/health")
def health() -> dict[str, str]:
    """Launcherの稼働状態を返す。"""
    return {"status": "ok", "app": "launcher"}


# アプリ一覧エンドポイントブロック。
@app.get("/api/apps")
def api_apps(request: Request) -> dict:
    """Launcherから開けるアプリ一覧を返す。"""
    _check_basic_auth(request)
    return _manager_get("/api/apps")


@app.get("/manage", response_class=HTMLResponse)
def manage(request: Request) -> HTMLResponse:
    """アプリ登録を管理する画面を返す。"""
    _check_basic_auth(request)
    return HTMLResponse(content=MANAGEMENT_HTML)


@app.get("/api/management/apps")
def management_apps(request: Request) -> dict:
    """管理画面へアプリ一覧を中継する。"""
    _check_basic_auth(request)
    return _manager_get("/api/apps")


@app.post("/api/management/apps")
def management_add(request: Request, payload: dict) -> dict:
    _check_basic_auth(request)
    return _manager_post_json("/api/apps", payload)


@app.post("/api/management/apps/{app_id}/{operation}")
def management_action(app_id: str, operation: str, request: Request) -> dict:
    _check_basic_auth(request)
    if operation not in {"start", "stop", "restart", "rebuild"}:
        raise HTTPException(400, "Unsupported operation")
    return _manager_post(f"/api/apps/{app_id}/{operation}")


@app.get("/api/management/apps/{app_id}/logs")
def management_logs(app_id: str, request: Request) -> dict:
    _check_basic_auth(request)
    return _manager_get(f"/api/apps/{app_id}/logs")


@app.delete("/api/management/apps/{app_id}")
def management_delete(app_id: str, request: Request, payload: dict) -> dict:
    _check_basic_auth(request)
    return _manager_delete(f"/api/apps/{app_id}", payload)


# 状態取得エンドポイントブロック。
@app.get("/api/status")
def api_status(request: Request) -> dict:
    """Manager APIから全アプリ状態を取得する。"""
    _check_basic_auth(request)
    logger.info("status requested")
    return _manager_get("/api/status")


# 開始エンドポイントブロック。
@app.post("/api/start/{app_name}")
def api_start(app_name: str, request: Request) -> dict:
    """指定アプリの開始をManager APIへ依頼する。"""
    _check_basic_auth(request)
    logger.info("start requested for %s", app_name)
    return _manager_post(f"/api/apps/{app_name}/start")


# 停止エンドポイントブロック。
@app.post("/api/stop/{app_name}")
def api_stop(app_name: str, request: Request) -> dict:
    """指定アプリの停止をManager APIへ依頼する。"""
    _check_basic_auth(request)
    logger.info("stop requested for %s", app_name)
    return _manager_post(f"/api/apps/{app_name}/stop")
