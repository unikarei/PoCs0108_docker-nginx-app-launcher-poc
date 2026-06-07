# GitHub Copilot 初期プロンプト

# WebApp Docker Nginx POC Project

## 目的

このプロジェクトは、Docker と Nginx の基本構造を理解するための POC、つまり検証用の最小Webアプリです。

本格的なアプリケーションを作ることが目的ではありません。
目的は、以下の仕組みを初心者でも理解できる形で確認することです。

* 簡単なWebアプリを作る
* 簡単なAPIを作る
* WebアプリをDockerコンテナで動かす
* Nginxをリバースプロキシとして使う
* ローカルの名前付きURLでアクセスできるようにする
* `/api` にアクセスするとAPIが動くことを確認する

---

## プロジェクト名

フォルダ名は以下とする。

```text
webapp-docker-nginx-poc
```

---

## 作りたい構成

ブラウザから以下のURLにアクセスできるようにする。

```text
http://test-function.local/
```

このURLにアクセスすると、簡単なWeb画面が表示される。

また、以下のURLにアクセスするとAPIが動作する。

```text
http://test-function.local/api/health
```

```text
http://test-function.local/api/add?a=1&b=2
```

---

## 技術スタック

初心者向けの最小構成にする。

使用する技術は以下とする。

* Python
* FastAPI
* Uvicorn
* Docker
* Docker Compose
* Nginx

今回は以下の技術は使わない。

* React
* Vue
* Next.js
* TypeScript
* データベース
* 認証機能
* HTTPS
* クラウドデプロイ
* CI/CD

---

## 重要な方針

このプロジェクトでは、シンプルさを最優先する。

GitHub Copilot は、以下の方針を必ず守ること。

1. 初心者が理解できるように、できるだけ単純な構成にすること
2. 不要な機能を追加しないこと
3. ファイル数を増やしすぎないこと
4. コードには初心者向けのコメントを入れること
5. Dockerfile、docker-compose.yml、Nginx設定には特に丁寧なコメントを入れること
6. 一度に大量のコードを作らず、Stepごとに実装すること
7. 変更したファイルと変更理由を毎回説明すること
8. まず設計用Markdownファイルを作ってから、実装コードを書くこと

---

## 最初に作成するMarkdownファイル

まず、実装コードを書く前に、以下の4つのMarkdownファイルを作成すること。

```text
CopilotInstruction.md
spec.md
architecture.md
task.md
```

---

# 1. CopilotInstruction.md に書く内容

`CopilotInstruction.md` には、このプロジェクトでCopilotが守るべき開発ルールを書く。

含める内容は以下。

* このプロジェクトの目的
* 初心者向けPOCであること
* シンプルさを最優先すること
* 不要な機能を追加しないこと
* Docker / Nginx / FastAPI の関係をわかりやすく説明すること
* 変更前に `spec.md`, `architecture.md`, `task.md` を確認すること
* Stepごとに小さく実装すること
* 各ファイルに初心者向けコメントを入れること
* Windows + Docker Desktop でも理解しやすい説明にすること

---

# 2. spec.md に書く内容

`spec.md` には、作成するPOCの仕様を書く。

## Web画面

`/` にアクセスすると、簡単なHTML画面を返す。

表示内容は以下。

```text
Test Function POC
This is a local Docker and Nginx POC application.
```

画面には、以下のAPI確認用リンクを表示する。

```text
/api/health
/api/add?a=1&b=2
```

## API仕様

### GET /api/health

以下のJSONを返す。

```json
{
  "status": "ok",
  "app": "test-function-poc"
}
```

### GET /api/add?a=1&b=2

クエリパラメータ `a` と `b` を受け取り、足し算結果を返す。

返却例。

```json
{
  "a": 1,
  "b": 2,
  "result": 3
}
```

---

# 3. architecture.md に書く内容

`architecture.md` には、システム構成を書く。

全体構成は以下。

```text
Browser
  |
  | http://test-function.local/
  v
Nginx Container
  |
  | proxy_pass
  v
FastAPI App Container
```

## app コンテナ

FastAPIアプリを動かす。

役割は以下。

* Web画面を返す
* APIを返す
* コンテナ内の8000番ポートで待ち受ける

## nginx コンテナ

Nginxを動かす。

役割は以下。

* ブラウザからのアクセスを受ける
* `test-function.local` という名前でアクセスを受ける
* Docker内部の `app:8000` に通信を転送する
* `/` も `/api` も FastAPIアプリへ転送する

## 通信の流れ

Web画面の場合。

```text
Browser
  -> http://test-function.local/
  -> Nginx
  -> app:8000
  -> FastAPI
  -> HTML response
```

APIの場合。

```text
Browser
  -> http://test-function.local/api/health
  -> Nginx
  -> app:8000/api/health
  -> FastAPI
  -> JSON response
```

---

# 4. task.md に書く内容

`task.md` には、実装作業を小さなStepに分けて書く。

## Step 1: フォルダ構成を作る

以下の構成にする。

```text
webapp-docker-nginx-poc/
  app/
    main.py
    requirements.txt
  nginx/
    default.conf
  Dockerfile
  docker-compose.yml
  README.md
  CopilotInstruction.md
  spec.md
  architecture.md
  task.md
```

## Step 2: FastAPIアプリを作る

作成するファイル。

```text
app/main.py
app/requirements.txt
```

実装する内容。

* `/` でHTMLを返す
* `/api/health` でJSONを返す
* `/api/add` で足し算結果を返す

## Step 3: Dockerfileを作る

FastAPIアプリをコンテナ化する。

含める内容。

* Python公式イメージを使う
* requirements.txt をインストールする
* appフォルダをコピーする
* uvicornでFastAPIを起動する

## Step 4: Nginx設定を作る

作成するファイル。

```text
nginx/default.conf
```

設定内容。

* `test-function.local` へのアクセスを受ける
* `app:8000` に proxy_pass する
* `/` と `/api` の両方をFastAPIへ転送する

## Step 5: docker-compose.ymlを作る

以下の2つのサービスを定義する。

* app
* nginx

nginx は外部の80番ポートを受ける。
app はDocker内部で8000番ポートを使う。

## Step 6: hostsファイルを設定する

Windowsのhostsファイルに以下を追加する前提で説明する。

```text
127.0.0.1 test-function.local
```

Windowsのhostsファイルの場所。

```text
C:\Windows\System32\drivers\etc\hosts
```

## Step 7: 起動確認する

以下のコマンドで起動する。

```bash
docker compose up --build
```

確認するURL。

```text
http://test-function.local/
http://test-function.local/api/health
http://test-function.local/api/add?a=1&b=2
```

## Step 8: 停止方法を書く

以下のコマンドで停止する。

```bash
docker compose down
```

---

## README.md に書く内容

README.md には、初心者向けに以下を説明する。

* このPOCの目的
* FastAPIの役割
* Dockerfileの役割
* docker-compose.ymlの役割
* Nginxの役割
* reverse proxy の意味
* proxy_pass の意味
* `test-function.local` の意味
* hostsファイルの意味
* `/api` の意味
* ブラウザからFastAPIまで通信が流れる仕組み
* 起動方法
* 停止方法
* 動作確認方法

---

## 実装時の注意

実装コードを書く前に、必ず以下の4ファイルを先に作成すること。

```text
CopilotInstruction.md
spec.md
architecture.md
task.md
```

その後、`task.md` のStepに従って、Step 1から順番に実装すること。

一度に全部を作らず、各Stepごとに以下を説明すること。

* 変更したファイル
* 変更した理由
* 次に確認すること

このPOCの目的は、完成度の高いWebアプリを作ることではなく、DockerとNginxの基本構造を理解することである。

そのため、余計な機能を追加せず、最小構成でわかりやすく作ること。
