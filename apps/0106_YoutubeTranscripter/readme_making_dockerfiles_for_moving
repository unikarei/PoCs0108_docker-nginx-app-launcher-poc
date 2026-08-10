このアプリは、YouTube の音声を取り込んで文字起こし・校正・エクスポートする Web アプリです。構成は、フロントエンドの Next.js、API の FastAPI、処理キューの Celery/Redis、永続化の PostgreSQL です。構成自体は README.md と docker-compose.yml にまとまっています。

### まず押さえるポイント
- Docker 版は、PostgreSQL と Redis をコンテナで起動します。
- DB は docker-compose.yml で `postgres_data` / `redis_data` ボリュームに保存されています。
- つまり「コンテナを再起動する分には残る」ことが多いですが、「ホストを変える」「ボリュームごと消す」「コンテナを完全に削除する」場合はデータが失われる可能性があります。

## 他の Docker 環境で動かす手順

### 1. まず対象ホストにコードを置く
- リポジトリをそのまま持っていきます。
- その後、.env.example を元に .env を作成します。

例:
```bash
cp .env.example .env
```

必要な値:
```env
OPENAI_API_KEY=...
POSTGRES_DB=youtube_transcription
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://postgres:your_secure_password_here@postgres:5432/youtube_transcription
REDIS_URL=redis://redis:6379/0
```

### 2. DB の保存方法を決める
このアプリでは DB をどこに置くかが最重要です。

#### パターンA: そのまま Docker 内の DB を使う
一番手軽です。ただし、永続化を確実にするために「ホスト側のディレクトリにマウント」するのがおすすめです。

docker-compose.yml の Postgres 部分を、たとえば次のように変更します。

```yaml
services:
  postgres:
    volumes:
      - /srv/youtube-transcripter/postgres:/var/lib/postgresql/data
```

Redis も同様に:
```yaml
services:
  redis:
    volumes:
      - /srv/youtube-transcripter/redis:/data
```

これで、コンテナを再作成してもデータがホスト側に残ります。

#### パターンB: 外部 DB/Redis を使う（おすすめ）
別の Docker ホストやクラウドの PostgreSQL/Redis を使う場合は、Compose 内の `postgres` / `redis` を使わずに外部接続に切り替えるのが安全です。

例:
```env
DATABASE_URL=postgresql://user:password@db.example.com:5432/youtube_transcription
REDIS_URL=redis://redis.example.com:6379/0
```

この場合、API/Worker/Frontend だけ起動すればよいです。

### 3. 起動
通常は次のように起動します。
```bash
docker compose up -d
```

もし DB を外部化している場合は、`postgres` と `redis` サービスを使わない構成にしたうえで、
```bash
docker compose up -d api worker frontend
```
のように起動します。

### 4. DB の移行・バックアップ
別環境へ移すときは、DB をそのままコピーするのが安全です。

#### バックアップ
旧環境で:
```bash
docker compose exec postgres pg_dump -U postgres youtube_transcription > backup.sql
```

#### 復元
新環境で:
```bash
docker compose exec -T postgres psql -U postgres -d youtube_transcription < backup.sql
```

必要なら、その後にマイグレーションも実行します。
```bash
docker compose run --rm migrate
```

## 追加で忘れない点
- 音声ファイルも audio_files 配下に出るので、必要ならこれもホスト側に残すようにしてください。
- もし Docker のボリュームをそのまま使うだけなら、ボリュームを消さないことが重要です。
- 本番寄りにするなら、PostgreSQL をコンテナ内ではなく外部の永続 DB にする方が安心です。

必要なら次に、あなたの環境向けに「別ホストで使うための compose 変更例」までそのまま書けます。