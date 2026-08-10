# SDD Initial Prompt: Docker Nginx App Launcher PoC

以下の指示に従い、Docker・Nginx・FastAPIを使った「複数アプリの
Launcher管理PoC」を、Spec-Driven Development（SDD）で実装してください。

## 目的

ローカルPC上で複数のFastAPIアプリをDockerコンテナとして実行し、Nginxを唯一の入口として、URLパスでアクセスできるようにします。Launcher画面から、登録済みアプリの確認、追加、編集、削除、起動、停止、再起動、再ビルド、ログ確認を行えるようにしてください。

例:

```text
http://localhost:8080/launcher/
http://localhost:8080/app1/
http://localhost:8080/app4/
http://localhost:8080/app5/
```

これは学習用・ローカル検証用PoCです。クラウド、Kubernetes、データベース、本番用認可、インターネット公開は実装しません。

## 最初に作成・更新するSDD成果物

実装より先に、次の4ファイルを作成または更新してください。

```text
.github/copilot-instructions.md
docs/spec.md
docs/architecture.md
docs/task.md
```

各ファイルの役割は次のとおりです。

| ファイル | 必須内容 |
| --- | --- |
| `copilot-instructions.md` | SDD手順、コーディング規約、禁止事項、検証規則 |
| `spec.md` | 目的、機能要件、API、登録項目、成功条件 |
| `architecture.md` | Browser/Nginx/Launcher/Manager API/Appの構成、ネットワーク、データフロー |
| `task.md` | 実装順序、各タスクの検証方法、完了チェックボックス |

実装中に要件・構成・運用方法が変わったら、必ず先にSDD文書を更新し、対応するタスクを追加してください。テスト成功後にのみタスクを`[x]`にしてください。

## 必須アーキテクチャ

```text
Browser
  │ http://localhost:8080
  ▼
Nginx container
  │ Docker internal network (multiapp_net)
  ├── Launcher container
  └── App containers

Launcher container
  │ HTTP only
  ▼
Manager API on host (127.0.0.1:9000)
  │ controlled Docker Compose commands
  ▼
Docker Engine
```

### 厳守事項

1. Nginxだけがホストへポート公開します。公開ポートは`8080:80`です。
2. Launcherと各Appはホストポートを公開しません。Docker内部ネットワークのポート8000だけを使います。
3. NginxはコンテナIPではなくDocker Composeサービス名で転送します。
4. LauncherはDockerコマンド、Docker SDK、Docker socketを使いません。
5. Launcherへ`/var/run/docker.sock`をマウントしてはいけません。
6. Docker操作はホスト側Manager APIだけが行います。
7. Manager APIは固定されたDocker Compose引数だけを実行し、リクエストで任意コマンドを受け取ってはいけません。
8. 生成物`generated/docker-compose.apps.yml`と`generated/nginx.conf`は手編集禁止です。

## 技術スタック

```text
Python 3.12
FastAPI
Uvicorn
HTTPX
Pydantic
Docker / Docker Compose
Nginx
plain HTML / JavaScript
Pytest
```

React、Vue、Next.js、データベース、Kubernetesは使用しません。

## アプリ契約

各アプリは`apps/<folder>/`に置き、次を持ちます。

```text
Dockerfile
requirements.txt
src/main.py
```

各アプリのFastAPIは以下を提供します。

```text
GET /           # HTML画面
GET /health     # JSON health
GET /api/test   # JSON success
```

HTML内のAPI呼び出しは`./api/test`のような相対URLにしてください。アプリはNginxのサブパス配下で動くためです。

各アプリ画面には日本語のDocker学習パネルを表示してください。

- Dockerイメージ: Pythonベースイメージ、依存ライブラリ、アプリソース、起動命令を含む再利用可能な実行パッケージ
- Dockerコンテナ: イメージから起動する実行単位。独立したプロセスとメモリーを持ち、内部ポート8000でNginxからの要求を受ける
- 再ビルドはイメージを作り直し、起動・再起動はコンテナを動かす操作であること

## 動的アプリ登録

登録情報は`config/apps.json`に原子的に保存してください。

| 項目 | 意味 |
| --- | --- |
| `display_name` | GUI表示名 |
| `app_id` | 不変の管理ID・Composeサービス名。英小文字、数字、ハイフンのみ |
| `source_directory` | Dockerビルド対象のプロジェクト相対フォルダー |
| `route_path` | ブラウザ公開URL。例`/app5/` |
| `internal_port` | コンテナ内部ポート |
| `health_path` | ヘルスチェックパス |
| `dockerfile` | ソースフォルダー内のDockerfile名 |

`app_id`、フォルダー名、URLパスは一致しなくても構いません。

例:

```text
app_id            = app4-revive
source_directory  = apps/app4
route_path        = /app4/
```

Openリンクは必ず`route_path`を使い、`app_id`からURLを推測してはいけません。

Manager APIは、登録情報から次を生成してください。

```text
generated/docker-compose.apps.yml
generated/nginx.conf
```

アプリ追加・編集・削除・再生成の後はNginxを再作成し、新しいルートを反映してください。Nginxは動的なDocker DNS名前解決を使い、未起動の新規アプリがあってもNginx自身は起動できるようにしてください。

## Launcher機能

Launcherには次を実装してください。

- 登録済みアプリ一覧と状態表示
- Open、Start、Stop、Restart、Rebuild、Logs、Edit、Delete
- アプリ追加フォーム
- プロジェクト・`apps/`配下を起点にしたフォルダーツリー選択
- app_id、表示名、ソースディレクトリの説明用`?`ダイアログ
- 起動・停止・再起動・再ビルドの違いを説明する`?`ダイアログ
- Delete時に「ソースも削除するか」を二段階確認

フォルダー選択はファイルをアップロードしてはいけません。選択されたプロジェクト相対パスだけをフォームへ設定し、Manager API側でDockerfileの存在を検証してください。

## Manager API操作

Manager APIは以下の操作を提供してください。

```text
GET    /health
GET    /api/apps
GET    /api/directories
POST   /api/apps
PATCH  /api/apps/{app_id}
DELETE /api/apps/{app_id}
POST   /api/apps/{app_id}/start
POST   /api/apps/{app_id}/stop
POST   /api/apps/{app_id}/restart
POST   /api/apps/{app_id}/rebuild
GET    /api/apps/{app_id}/logs
POST   /api/generate
```

Startは、新規登録直後にも動くように次を使ってください。

```text
docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml up -d --build <app_id>
```

単純な`docker compose start <app_id>`は、まだコンテナが存在しない新規アプリには使えません。

削除時はソースを残すことを既定値にしてください。ソース削除を許可するのは`apps/`配下の実ディレクトリだけです。プロジェクトルート、`apps`ルート、シンボリックリンク、プロジェクト外パスは拒否してください。

## 実装・コメント規約

- 初心者が読める小さく明示的なPythonとHTMLにしてください。
- 大きな処理単位・関数の直前に目的を説明するコメントを置いてください。
- 行内コメントを付ける場合は、開始列を可能な限り揃えてください。
- 明確なエラーを返し、例外やDocker失敗を握りつぶさないでください。

## 必須テストと運用確認

Python変更後:

```text
python -m pytest -q
```

Windowsでの起動:

```text
scripts\run50_start_all.bat
```

確認:

```text
scripts\run35_docker_status.bat
scripts\run40_nginx_check.bat
scripts\run41_app_health_check.bat
scripts\run42_manager_check.bat
```

動的アプリ追加後は、少なくとも以下を確認してください。

1. Dockerfileを持つ`apps/<new-app>/`を作る
2. 管理画面から一意の`app_id`と`route_path`で登録する
3. 生成Compose・Nginx設定に項目が追加される
4. 初回Startでビルド・コンテナ作成・起動ができる
5. Nginx経由で`route_path`と`route_path + health`がHTTP 200になる
6. Stop、Start、Rebuild、Restart、Delete（ソース保持／ソース削除）を確認する

完了時は、変更したSDD文書、実装ファイル、テスト結果、Docker実行結果、残る制約を簡潔に報告してください。
