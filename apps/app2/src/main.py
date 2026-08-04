from fastapi import FastAPI                 # FastAPI本体を読み込む。
from fastapi.responses import HTMLResponse  # HTMLを返すレスポンス型を読み込む。

# アプリケーション構築ブロック: App2用のFastAPIインスタンスを作成する。
app = FastAPI(title="App2")                # OpenAPI画面に表示する名称を設定する。

# 画面テンプレートブロック: App2のHTML画面を定義する。
HOME_PAGE_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>App2</title>
  </head>
  <body>
    <main>
      <h1>App2</h1>
      <!-- Docker learning panel: explain this application's image and container. -->
      <section aria-label="Dockerの説明">
        <h2>このApp2のDockerイメージとコンテナ</h2>
        <p><strong>Dockerイメージ</strong>は、App2を動かすための再利用できる実行用パッケージです。Python 3.12-slim、FastAPI、Uvicorn、App2の<code>src</code>ソース、Uvicornの起動命令を含みます。</p>
        <p><strong>Dockerコンテナ</strong>は、そのイメージから実際に起動しているApp2の実行単位です。独立したプロセスと実行中のメモリー状態を持ち、Docker内部ネットワークのポート8000でNginxからの要求を受けます。</p>
        <p>ソースコード・Dockerfile・依存ライブラリを変更した場合は「再ビルド」でイメージを作り直します。起動・再起動は既存イメージからコンテナを動かす操作です。</p>
      </section>
      <button id=\"test-button\">Run App2 Test</button>
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


# ルートエンドポイントブロック: App2の画面を返す。
@app.get("/", response_class=HTMLResponse)  # GET / をHTMLレスポンスに割り当てる。
def home() -> HTMLResponse:
    """App2の静的HTML画面を返す。"""
    return HTMLResponse(content=HOME_PAGE_HTML)  # 定義済みHTMLをレスポンスとして返す。


# ヘルスチェックブロック: コンテナ稼働確認用のJSONを返す。
@app.get("/health")                         # GET /health をハンドラに割り当てる。
def health() -> dict[str, str]:
    """App2の稼働状態を返す。"""
    return {"status": "ok", "app": "app2"}  # 固定の稼働確認結果を返す。


# APIテストブロック: 画面のボタンから呼ばれるバックエンドAPI。
@app.get("/api/test")                        # GET /api/test をハンドラに割り当てる。
def api_test() -> dict[str, str]:
    """App2固有の成功メッセージを返す。"""
    return {
        "status": "success",                 # API処理が成功したことを示す。
        "message": "App2 backend responded successfully.",  # 画面に表示するメッセージ。
    }
