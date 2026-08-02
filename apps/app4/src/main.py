from fastapi import FastAPI                 # FastAPI本体を読み込む。
from fastapi.responses import HTMLResponse  # HTMLレスポンス型を読み込む。

# アプリケーション構築ブロック: App4のFastAPIアプリを作成する。
app = FastAPI(title="App4")                # APIドキュメント用の名称を設定する。

# 画面テンプレートブロック: App4のHTMLを保持する。
HOME_PAGE_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>App4</title>
  </head>
  <body>
    <main>
      <h1>App4</h1>
      <button id=\"test-button\">Run App4 Test</button>
      <p id=\"result\"></p>
    </main>
    <script>
      const button = document.getElementById('test-button');
      const result = document.getElementById('result');

      button.addEventListener('click', async () => {
        result.textContent = 'Running...';
        const response = await fetch('./api/test');
        const data = await response.json();
        result.textContent = data.message;
      });
    </script>
  </body>
</html>
"""


# 画面エンドポイントブロック: App4の画面を返す。
@app.get("/", response_class=HTMLResponse)  # GET / を登録する。
def home() -> HTMLResponse:
    """App4の画面を返す。"""
    return HTMLResponse(content=HOME_PAGE_HTML)  # HTML本文を返す。


# ヘルスチェックブロック: 稼働状態を返す。
@app.get("/health")                         # GET /health を登録する。
def health() -> dict[str, str]:
    """App4の稼働状態を返す。"""
    return {"status": "ok", "app": "app4"}  # 固定の正常状態を返す。


# APIテストブロック: 画面のボタンから呼び出される。
@app.get("/api/test")                        # GET /api/test を登録する。
def api_test() -> dict[str, str]:
    """App4の成功メッセージを返す。"""
    return {
        "status": "success",
        "message": "App4 backend responded successfully.",
    }
