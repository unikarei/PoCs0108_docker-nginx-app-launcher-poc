# readme_run.md

# Docker + Nginx Multiapp Launcher 実行スクリプト説明書

## 1. このファイルの目的

この文書は、本プロジェクトを支える `scripts/` 配下の実行スクリプト群を説明するものです。

本プロジェクトは、以下の構成を前提にしています。

```text
Browser
  ↓
Nginx
  ↓
Docker internal network
  ↓
launcher / app1 / app2 / app3 / app4
```

また、アプリの起動・停止は安全寄りの方式Bを採用します。

```text
Launcher
  ↓
Manager API
  ↓
docker compose start / stop / ps
```

重要な方針は以下です。

```text
Launcher に Docker socket をマウントしない
Launcher から Docker を直接操作しない
Manager API をホスト側で起動する
Nginx だけをホスト側に公開する
```

---

## 2. スクリプト構成

本プロジェクトでは、Windows用 `.bat` と Linux/macOS/WSL用 `.sh` を両方用意します。

```text
scripts/
├─ run10_uv_venv.bat
├─ run10_uv_venv.sh
├─ run11_uv_sync.bat
├─ run11_uv_sync.sh
├─ run20_manager_start.bat
├─ run20_manager_start.sh
├─ run21_manager_stop.bat
├─ run21_manager_stop.sh
├─ run30_docker_init.bat
├─ run30_docker_init.sh
├─ run31_docker_start_dev.bat
├─ run31_docker_start_dev.sh
├─ run32_docker_start_detached.bat
├─ run32_docker_start_detached.sh
├─ run33_docker_stop.bat
├─ run33_docker_stop.sh
├─ run34_docker_log.bat
├─ run34_docker_log.sh
├─ run35_docker_status.bat
├─ run35_docker_status.sh
├─ run40_nginx_check.bat
├─ run40_nginx_check.sh
├─ run41_app_health_check.bat
├─ run41_app_health_check.sh
├─ run42_manager_check.bat
├─ run42_manager_check.sh
├─ run50_start_all.bat
├─ run50_start_all.sh
├─ run51_stop_all.bat
├─ run51_stop_all.sh
├─ start.bat
├─ start.sh
├─ stop.bat
├─ stop.sh
├─ status.bat
├─ status.sh
├─ manager_start.bat
├─ manager_start.sh
├─ manager_stop.bat
└─ manager_stop.sh
```

---

## 3. Quick Start

## 3.1 Windowsの場合

最初にPython仮想環境を作ります。

```bat
scripts\run10_uv_venv.bat
```

依存関係を同期します。

```bat
scripts\run11_uv_sync.bat
```

全体を起動します。

```bat
scripts\run50_start_all.bat
```

ブラウザで開きます。

```text
http://localhost:8080/launcher/
```

全体を停止します。

```bat
scripts\run51_stop_all.bat
```

---

## 3.2 Linux / macOS / WSL の場合

最初に実行権限を付けます。

```bash
chmod +x scripts/*.sh
```

Python仮想環境を作ります。

```bash
./scripts/run10_uv_venv.sh
```

依存関係を同期します。

```bash
./scripts/run11_uv_sync.sh
```

全体を起動します。

```bash
./scripts/run50_start_all.sh
```

ブラウザで開きます。

```text
http://localhost:8080/launcher/
```

全体を停止します。

```bash
./scripts/run51_stop_all.sh
```

---

## 4. 各スクリプトの役割

## 4.1 環境準備系

### run10_uv_venv

Python仮想環境 `.venv` を作成します。

使用場面：

```text
初回セットアップ時
Manager API をホスト側で起動したい時
```

---

### run11_uv_sync

Python依存関係をインストールします。

優先順位は以下です。

```text
1. ルート直下に pyproject.toml があれば uv sync
2. なければ manager-api / launcher / apps の requirements.txt を読む
```

---

## 4.2 Manager API系

### run20_manager_start

ホスト側で Manager API を起動します。

Manager API は以下の役割を持ちます。

```text
docker compose ps
docker compose start app1
docker compose stop app1
docker compose start app2
docker compose stop app2
docker compose start app3
docker compose stop app3
docker compose start app4
docker compose stop app4
```

起動後の確認URLは以下です。

```text
http://127.0.0.1:9000/health
```

---

### run21_manager_stop

ホスト側で起動した Manager API を停止します。

`.run/manager-api.pid` に保存されたPIDを使って停止します。

---

## 4.3 Docker基本操作系

### run30_docker_init

Dockerと主要ファイルの存在を確認します。

確認内容：

```text
docker コマンドが存在するか
docker compose が使えるか
Docker Engine が起動しているか
docker-compose.yml が存在するか
nginx/nginx.conf が存在するか
各アプリの Dockerfile が存在するか
manager-api/src/main.py が存在するか
```

---

### run31_docker_start_dev

Docker Composeを前面起動します。

ログをそのまま画面に出します。

開発中にエラーを見ながら動かす場合に使います。

```text
docker compose up --build
```

---

### run32_docker_start_detached

Docker Composeをバックグラウンド起動します。

通常起動で使います。

```text
docker compose up --build -d
```

---

### run33_docker_stop

Docker Compose一式を停止します。

```text
docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml down
```

---

### run34_docker_log

Dockerログを表示します。

全サービスのログを見る場合：

```bat
scripts\run34_docker_log.bat
```

または

```bash
./scripts/run34_docker_log.sh
```

特定サービスだけ見る場合：

```bat
scripts\run34_docker_log.bat nginx
```

または

```bash
./scripts/run34_docker_log.sh nginx
```

---

### run35_docker_status

Docker Composeのコンテナ状態を確認します。

```text
docker compose ps
```

---

## 4.4 確認系

### run40_nginx_check

Nginxリバースプロキシ経由のURLを確認します。

LauncherはBasic認証が有効なため、`/launcher/` の確認はBasic認証付きで実行します。

認証情報は以下の環境変数で上書きできます。

```text
LAUNCHER_BASIC_AUTH_USER
LAUNCHER_BASIC_AUTH_PASSWORD
```

確認対象：

```text
http://localhost:8080/launcher/
http://localhost:8080/app1/
http://localhost:8080/app2/
http://localhost:8080/app3/
http://localhost:8080/app4/
```

---

### run41_app_health_check

各アプリのヘルスチェックURLを確認します。

確認対象：

```text
http://localhost:8080/launcher/health
http://localhost:8080/app1/health
http://localhost:8080/app2/health
http://localhost:8080/app3/health
http://localhost:8080/app4/health
```

---

### run42_manager_check

Manager APIの疎通を確認します。

確認対象：

```text
http://127.0.0.1:9000/health
http://127.0.0.1:9000/api/status
```

---

## 4.5 一括操作系

### run50_start_all

以下を順番に実行します。

```text
1. Docker事前確認
2. Manager API起動
3. Docker Composeバックグラウンド起動
4. Docker状態表示
5. Launcher URL表示
```

初心者向けの標準起動スクリプトです。

---

### run51_stop_all

以下を順番に実行します。

```text
1. Docker Compose停止
2. Manager API停止
```

初心者向けの標準停止スクリプトです。

---

## 4.6 互換ラッパー

以下のスクリプトは、run番号付きスクリプトへ委譲する互換エントリです。

```text
start.*         -> run50_start_all.*
stop.*          -> run51_stop_all.*
status.*        -> run35_docker_status.*
manager_start.* -> run20_manager_start.*
manager_stop.*  -> run21_manager_stop.*
```

既存手順を維持したい場合は、これらのラッパーを使っても問題ありません。

---

## 5. 推奨する日常運用

## 5.1 普通に起動したい場合

Windows：

```bat
scripts\run50_start_all.bat
```

Linux / macOS / WSL：

```bash
./scripts/run50_start_all.sh
```

---

## 5.2 ログを見たい場合

Windows：

```bat
scripts\run34_docker_log.bat
```

Linux / macOS / WSL：

```bash
./scripts/run34_docker_log.sh
```

---

## 5.3 状態を確認したい場合

Windows：

```bat
scripts\run35_docker_status.bat
```

Linux / macOS / WSL：

```bash
./scripts/run35_docker_status.sh
```

---

## 5.4 停止したい場合

Windows：

```bat
scripts\run51_stop_all.bat
```

Linux / macOS / WSL：

```bash
./scripts/run51_stop_all.sh
```

---

## 6. 注意点

## 6.1 Manager APIはホスト側で起動する

本プロジェクトは方式Bを採用しています。

そのため、Manager APIはDocker内部ではなく、ホスト側で起動する想定です。

理由は、LauncherコンテナにDocker socketを渡さないためです。

---

## 6.2 Docker socket mountは禁止

以下のような設定は使いません。

```yaml
- /var/run/docker.sock:/var/run/docker.sock
```

これは強力すぎる権限をLauncherに渡してしまうためです。

---

## 6.3 初期段階ではエラーが出てよい

STEP1時点では、まだ以下のファイルが存在しない可能性があります。

```text
docker-compose.yml
nginx/nginx.conf
manager-api/src/main.py
launcher/Dockerfile
apps/app1/Dockerfile
apps/app2/Dockerfile
apps/app3/Dockerfile
```

その場合、確認スクリプトは `[WARN]` または `[ERROR]` を表示します。

これは異常ではなく、未実装のタスクが残っていることを示しています。

---

## 7. Copilotへの実装指示例

Copilotにスクリプト整備を依頼する場合は、以下のように指示します。

```text
scripts 配下の .bat と .sh を確認してください。
各行のコメント形式を維持してください。
処理を変更する場合も、コメント開始位置を可能な限りそろえてください。
方式Bを維持し、LauncherにDocker socketをマウントしないでください。
```
