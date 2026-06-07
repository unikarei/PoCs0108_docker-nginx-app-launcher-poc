from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="App1")

HOME_PAGE_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>App1</title>
  </head>
  <body>
    <main>
      <h1>App1</h1>
      <button id=\"test-button\">Run App1 Test</button>
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


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(content=HOME_PAGE_HTML)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "app1"}


@app.get("/api/test")
def api_test() -> dict[str, str]:
    return {
        "status": "success",
        "message": "App1 backend responded successfully.",
    }
