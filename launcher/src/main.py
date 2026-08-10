import os                         # 環境変数を読み込む。
import base64                     # Basic認証ヘッダーをデコードする。
import logging                    # 操作履歴を記録する。
import secrets                    # 認証情報を安全に比較する。

import httpx                      # Manager APIへHTTPリクエストを送る。
from fastapi import FastAPI, HTTPException, Request  # API本体とリクエスト型。
from fastapi.responses import HTMLResponse           # HTMLレスポンス型。

# 設定ブロック: 起動時に環境変数を読み、許可範囲とタイムアウトを定める。
ALLOWED_APPS = ["app1", "app2", "app3", "app4"]
# Launcher overview:
# This module serves the browser-facing list and management pages. It has no
# Docker socket or project-file access. After Basic authentication, it forwards
# approved HTTP requests to the host-side Manager API, which owns all Docker
# and registry operations.
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
      .danger { color: #a00; }
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

      // Row rendering block: keep the control id separate from the public route.
      function rowHtml(appName, routePath, statusText) {
        return `
          <tr data-app="${appName}">
            <td>${appName}</td>
            <td class="status">${statusText}</td>
            <td>
              <div class="actions">
                <a href="../${routePath.replace(/^\\//, '')}" target="_blank" rel="noopener">Open</a>
                <button data-action="start" data-app="${appName}">Start</button>
                <button data-action="stop" data-app="${appName}">Stop</button>
                <button data-action="delete" data-app="${appName}" class="danger">Delete</button>
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

          tbody.innerHTML = APPS.map((item) => rowHtml(item.app_id, item.route_path || `/${item.app_id}/`, statusMap[item.app_id] || 'unknown')).join('');
          bindActionButtons();
          setMessage('Status updated.');
        } catch (error) {
          setMessage('Manager APIに接続できません。');
        }
      }

      async function callAction(action, appName) {
        try {
          if (action === 'delete') {
            await deleteApp(appName);
            return;
          }
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

      async function deleteApp(appName) {
        const removeSource = confirm(
          `${appName} の登録とDockerサービスを削除します。\n\nソースディレクトリも削除しますか？\n\n` +
          '「OK」= ソースディレクトリも削除\\n「キャンセル」= GUI登録とDockerサービスのみ削除'
        );
        const finalMessage = removeSource
          ? `${appName} のソースディレクトリも完全に削除します。\\nこの操作は取り消せません。続行しますか？`
          : `${appName} をGUIとDockerから削除します。ソースは残します。続行しますか？`;
        if (!confirm(finalMessage)) return;
        const response = await fetch(`./api/delete/${appName}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirm_app_id: appName, remove_source: removeSource }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Delete failed');
        setMessage(payload.message || `${appName} deleted.`);
        await refreshStatus();
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
<style>body{font-family:sans-serif;margin:2rem}input,textarea{display:block;width:100%;max-width:520px;margin:.25rem 0 .75rem;padding:.4rem}button{margin:.2rem;padding:.4rem}.help-wrap{display:inline-block;position:relative}.help-wrap summary{list-style:none;border:0;border-radius:50%;background:#2684ff;color:#fff;width:1.5rem;height:1.5rem;line-height:1.5rem;text-align:center;cursor:pointer}.help-wrap summary::-webkit-details-marker{display:none}.popup{position:fixed;z-index:10;left:50%;top:25%;transform:translateX(-50%);background:#fff;border:1px solid #777;border-radius:.4rem;box-shadow:0 4px 18px #999;padding:1rem;max-width:420px}.popup li{margin:.35rem 0}.danger{background:#fdd}.card{border:1px solid #ddd;padding:1rem;margin:1rem 0}.tabs{display:flex;gap:.25rem;border-bottom:1px solid #bbb;margin:1rem 0}.tab{border:1px solid transparent;border-radius:.3rem .3rem 0 0;background:#eee;margin:0;padding:.55rem .9rem;cursor:pointer}.tab[aria-selected="true"]{background:#fff;border-color:#bbb;border-bottom-color:#fff;font-weight:bold}.tab-panel[hidden]{display:none}</style></head>
<body><p><a href="./">← Launcher</a></p><h1>アプリ管理 ⚙</h1><p id="message"></p><div class="tabs" role="tablist" aria-label="アプリ管理メニュー"><button id="tab-add-button" class="tab" role="tab" aria-controls="tab-add" aria-selected="true" onclick="switchTab('add')">追加</button><button id="tab-registered-button" class="tab" role="tab" aria-controls="tab-registered" aria-selected="false" onclick="switchTab('registered')">登録済みアプリ</button></div>
<section id="tab-add" class="tab-panel card" role="tabpanel" aria-labelledby="tab-add-button"><h2>追加</h2><form id="add-form"><label>表示名 <details class="help-wrap"><summary aria-label="表示名の説明">?</summary><div class="popup" role="dialog"><h2>表示名とは？</h2><p>Launcher画面に表示する、人間向けのアプリ名です。</p><ul><li>日本語や空白を使用できます。</li><li>Dockerサービス名やURLには使いません。</li><li>例：<code>売上分析アプリ</code></li></ul><button type="button" onclick="this.closest('details').removeAttribute('open')">閉じる</button></div></details><input name="display_name" required></label><label>app_id <details class="help-wrap"><summary aria-label="app_idの説明">?</summary><div id="app-id-help" class="popup" role="dialog"><h2 id="app-id-help-title">app_idとは？</h2><p>アプリを内部で識別するための一意なIDです。</p><ul><li>Docker Composeのサービス名に使います。</li><li>Nginxの転送先名とURLパスに使います。</li><li>起動・停止・削除対象の識別に使います。</li></ul><p>英小文字、数字、ハイフンのみ入力できます。</p><p>例：<code>sales-analysis</code>、<code>app5</code>、<code>customer-api</code></p><p>登録後は基本的に変更しないでください。</p><button type="button" onclick="this.closest('details').removeAttribute('open')">閉じる</button></div></details><input name="app_id" pattern="[a-z0-9-]+" required></label><label>ソースディレクトリ <details class="help-wrap"><summary aria-label="ソースディレクトリの説明">?</summary><div class="popup" role="dialog"><h2>ソースディレクトリとは？</h2><p>アプリのソースコードとDockerfileが保存されているフォルダーです。</p><ul><li>Dockerイメージのビルド対象になります。</li><li>プロジェクト基準の相対パスを入力できます。</li><li>例：<code>apps/sales</code></li><li>指定フォルダー内にDockerfileが必要です。</li></ul><button type="button" onclick="this.closest('details').removeAttribute('open')">閉じる</button></div></details><button type="button" onclick="chooseSourceFolder()">フォルダーを参照...</button><input name="source_directory" id="source-directory-text" value="apps" required><input id="source-folder-picker" type="file" webkitdirectory directory multiple style="display:none"></label><label>URLパス<input name="route_path" placeholder="/my-app/"></label><label>内部ポート<input name="internal_port" type="number" value="8000" min="1" max="65535"></label><label>ヘルスパス<input name="health_path" value="/health"></label><label>Dockerfile<input name="dockerfile" value="Dockerfile"></label><label>説明<textarea name="description"></textarea></label><button>登録</button></form></section>
<section id="tab-registered" class="tab-panel" role="tabpanel" aria-labelledby="tab-registered-button" hidden><h2>登録済みアプリ</h2><div id="apps"></div></section>
<dialog id="source-folder-dialog"><form method="dialog"><h3>ソースフォルダーを選択</h3><p>プロジェクトフォルダーとapps配下から選択してください。</p><select id="source-folder-tree" size="10" style="min-width:320px"></select><div><button value="cancel">キャンセル</button><button id="source-folder-apply" value="default">選択</button></div></form></dialog>
<dialog id="lifecycle-help-dialog"><form method="dialog"><h3>起動・停止・再起動・再ビルドの説明</h3><h4>起動</h4><p>停止しているコンテナを開始します。すでに作成済みのDockerイメージを使うため、通常は最も短時間で完了します。ソースコード、Dockerfile、依存ライブラリを変更していない場合は、まず「起動」を使います。すでに動いている場合は、そのままの状態を維持します。</p><h4>停止</h4><p>実行中のコンテナを停止します。登録情報、ソースコード、Dockerイメージ、ログは削除しません。停止中はOpenしてもアプリを表示できません。再度使うときは「起動」を押してください。</p><h4>再起動</h4><p>コンテナをいったん停止してから、同じイメージで再び起動します。アプリの一時メモリー状態や接続状態をリセットしたい場合、または環境変数などコンテナ起動時に読む設定を反映したい場合に使います。ソースコードやDockerfileを変更しただけでは、再起動しても新しいイメージにはなりません。</p><h4>再ビルド</h4><p>Dockerfile、requirements.txtなどの依存定義、またはソースコードの変更をDockerイメージへ反映するために、イメージを作り直します。ビルド完了後、必要に応じて「再起動」または「起動」を押し、新しいイメージでコンテナを動かしてください。依存ライブラリの取得があるため、通常は他の操作より時間がかかります。</p><h4>使い分け</h4><p>停止中のアプリを使う: 起動。動作をリセットしたい: 再起動。Dockerfile・依存ライブラリ・ソースを反映したい: 再ビルド後に再起動。アプリを不要にする: 停止。登録そのものを消す: 削除。</p><button>閉じる</button></form></dialog>
<script>
const message=document.getElementById('message'); const apps=document.getElementById('apps');
// Bundle-registration block: collect only structural Compose metadata, never secrets.
document.getElementById('add-form').insertAdjacentHTML('afterbegin','<fieldset><legend>登録形式</legend><label><select name="deployment_type" id="deployment-type"><option value="single">単体アプリ</option><option value="bundle">Compose バンドル</option></select></label><div id="bundle-fields" hidden><label>Compose ファイル<input name="compose_file" value="docker-compose.launcher.yml"></label><label>公開サービス名<input name="public_service" placeholder="frontend"></label><p>API キーやパスワードは入力しません。対象フォルダーの .env で管理します。</p></div></fieldset>');
document.getElementById('deployment-type').addEventListener('change',e=>{document.getElementById('bundle-fields').hidden=e.target.value!=="bundle"});
// Tab-navigation block: keep the form and registered-app list focused in separate panels.
function switchTab(name){const showAdd=name==='add';document.getElementById('tab-add').hidden=!showAdd;document.getElementById('tab-registered').hidden=showAdd;document.getElementById('tab-add-button').setAttribute('aria-selected',String(showAdd));document.getElementById('tab-registered-button').setAttribute('aria-selected',String(!showAdd));}
// Folder-selection block: load the project tree before using the native picker.
async function chooseSourceFolder(){
  const dialog=document.getElementById('source-folder-dialog'); // Locate the modal dialog.
  const tree=document.getElementById('source-folder-tree');     // Locate its directory list.
  try{
    const response=await fetch('./api/management/directories');  // Ask Manager for safe relative paths.
    if(!response.ok) throw new Error('directory API unavailable');
    const payload=await response.json();
    tree.innerHTML='';
    (payload.directories||['.','apps']).forEach(path=>{
      const option=document.createElement('option');
      option.value=path; option.textContent=path==='.'?'プロジェクトフォルダー':path;
      tree.appendChild(option);
    });
    const initial=[...tree.options].find(option=>option.value.toLowerCase()==='apps');
    if(initial) tree.value=initial.value;
    dialog.showModal();
    return;
  }catch(error){
    say('フォルダー一覧を取得できません。標準選択を開きます。');
  }
  if(window.showDirectoryPicker){
    try{
      // The browser remembers the last folder for this stable picker id.
      // The source field itself starts at the project-relative apps directory.
      const handle=await window.showDirectoryPicker({id:'launcher-source-folder',mode:'read'});
      const name=handle.name||'apps';
      const value=name.toLowerCase()==='apps'?'apps':'apps/'+name;
      document.getElementById('source-directory-text').value=value;
      say('選択したフォルダー: '+value);
    }catch(error){
      if(error && error.name!=='AbortError') say('フォルダーを選択できません: '+error.message);
    }
    return;
  }
  const picker=document.getElementById('source-folder-picker');
  picker.style.cssText='position:absolute;opacity:0;width:1px;height:1px;pointer-events:none';
  if(picker.showPicker) picker.showPicker(); else picker.click();
}
// Folder confirmation block: copy only the selected path into the form.
document.getElementById('source-folder-apply').addEventListener('click',e=>{
  const tree=document.getElementById('source-folder-tree');
  if(!tree.value){e.preventDefault();return;}
  document.getElementById('source-directory-text').value=tree.value;
  say('選択したフォルダー: '+tree.value);
});
document.getElementById('source-folder-picker').addEventListener('change',e=>{const files=e.target.files;if(!files.length)return;const first=(files[0].webkitRelativePath||'').split('/')[0];const value=first?('apps/'+first):'apps';document.getElementById('source-directory-text').value=value;say('選択したフォルダー: '+value)})
function say(t){message.textContent=t} function esc(t){return String(t).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
// Lifecycle-help block: show the shared explanatory dialog without changing app state.
function showLifecycleHelp(){document.getElementById('lifecycle-help-dialog').showModal()}
async function load(){const r=await fetch('./api/management/apps');if(!r.ok){say('Manager APIに接続できません');return}const p=await r.json();apps.innerHTML=p.apps.map(a=>`<article class="card"><b>${esc(a.display_name)}</b> (${esc(a.app_id)})<br>URL: ${esc(a.route_path)}<br>ソース: ${esc(a.source_directory)}<br><button onclick="editApp('${a.app_id}','${esc(a.display_name)}','${esc(a.description||'')}')">編集</button><button onclick="action('${a.app_id}','start')">起動</button><button onclick="action('${a.app_id}','stop')">停止</button><button onclick="action('${a.app_id}','restart')">再起動</button><button onclick="action('${a.app_id}','rebuild')">再ビルド</button><button onclick="showLogs('${a.app_id}')">ログ</button><button class="danger" onclick="removeApp('${a.app_id}','${esc(a.display_name)}')">削除</button><button type="button" aria-label="起動・停止・再起動・再ビルドの説明" onclick="showLifecycleHelp()" style="background:#2684ff;color:#fff;border:0;border-radius:50%;width:1.5rem;height:1.5rem;line-height:1.5rem;padding:0;font-weight:bold">?</button></article>`).join('')}
async function editApp(id,name,description){const display_name=prompt('表示名',name);if(display_name===null)return;const nextDescription=prompt('説明',description);if(nextDescription===null)return;const r=await fetch('./api/management/apps/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name,description:nextDescription})});const p=await r.json();say(p.message||p.detail||'更新完了');load()}
async function action(id,op){say(op+' '+id+'...');const r=await fetch('./api/management/apps/'+id+'/'+op,{method:'POST'});const p=await r.json();say(p.message||p.detail||'完了');load()}
async function showLogs(id){const r=await fetch('./api/management/apps/'+id+'/logs');const p=await r.json();alert(p.logs||p.detail||'ログなし')}
async function removeApp(id,name){if(!confirm('登録とDockerサービスを削除します。ソースコードは残します。'+String.fromCharCode(10)+name+' ('+id+')'))return;const r=await fetch('./api/management/apps/'+id,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm_app_id:id,remove_source:false})});const p=await r.json();say(p.message||p.detail||'削除完了');load()}
document.getElementById('add-form').addEventListener('submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));data.internal_port=Number(data.internal_port);const r=await fetch('./api/management/apps',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const p=await r.json();say(p.message||p.detail||'登録完了');if(r.ok){e.target.reset();document.getElementById('source-directory-text').value='apps'}load()});load();
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
        response = httpx.request("DELETE", f"{MANAGER_API_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
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


@app.get("/api/management/directories")
def management_directories(request: Request) -> dict:
    """管理画面へソースディレクトリ候補を中継する。"""
    _check_basic_auth(request)
    return _manager_get("/api/directories")


@app.post("/api/management/apps")
def management_add(request: Request, payload: dict) -> dict:
    """Forward a new app registration after authenticating the browser request."""
    _check_basic_auth(request)
    return _manager_post_json("/api/apps", payload)


@app.post("/api/management/apps/{app_id}/{operation}")
def management_action(app_id: str, operation: str, request: Request) -> dict:
    """Forward an approved lifecycle action and reject unsupported operations."""
    _check_basic_auth(request)
    if operation not in {"start", "stop", "restart", "rebuild"}:
        raise HTTPException(400, "Unsupported operation")
    return _manager_post(f"/api/apps/{app_id}/{operation}")


@app.get("/api/management/apps/{app_id}/logs")
def management_logs(app_id: str, request: Request) -> dict:
    """Return bounded logs for one registered app through the Manager API."""
    _check_basic_auth(request)
    return _manager_get(f"/api/apps/{app_id}/logs")


@app.delete("/api/management/apps/{app_id}")
def management_delete(app_id: str, request: Request, payload: dict) -> dict:
    """Forward a confirmed registration deletion request to the Manager API."""
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


@app.delete("/api/delete/{app_name}")
def api_delete(app_name: str, request: Request, payload: dict) -> dict:
    """削除確認済みのアプリをManager APIへ中継する。"""
    _check_basic_auth(request)
    if payload.get("confirm_app_id") != app_name:
        raise HTTPException(status_code=400, detail="Delete confirmation does not match app_id")
    return _manager_delete(f"/api/apps/{app_name}", payload)
