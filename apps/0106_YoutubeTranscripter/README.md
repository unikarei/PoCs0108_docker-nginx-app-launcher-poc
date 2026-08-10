# YouTube Transcription Web App

YouTube動画の音声を抽出し、日本語・英語の文字起こしとLLM校正を提供するWebアプリケーション。

## Features

- YouTube動画URLからの音声抽出
- 日本語・英語の高精度文字起こし（OpenAI Whisper API）
- LLMによるテキスト校正（GPT-4o）
- 複数形式でのエクスポート（TXT、SRT、VTT）
- 非同期処理による高速な処理
- レスポンシブなWebUI
- **バッチ処理**: URLリスト、CSV、プレイリスト/チャンネル展開による一括処理
- **フォルダツリーライブラリ**: 階層フォルダで動画を整理、タグ付け、一括操作
- **検索・フィルタ**: キーワード、タグ、ステータス、期間での絞り込み
- **Q&A機能**: 文字起こし結果に対する質問応答（LLM活用）

## Folder Tree Library (New!)

動画をフォルダで階層的に管理し、効率的に整理・検索できます：

### 主な機能
- **階層フォルダ管理**: フォルダツリーで動画を分類・整理
- **タグ機能**: 横断的な整理と検索
- **一括操作**: 複数動画の移動、タグ付け、削除
- **検索・フィルタ**: キーワード、タグ、ステータスで絞り込み
- **フォルダ既定値**: フォルダごとに言語・モデルを設定
- **ステータス集計**: フォルダごとに進行状況を可視化

### データ移行

既存の動画データをフォルダ構造に移行するには：

```bash
# Dry run (実際には変更しない)
python scripts/migrate_jobs_to_items.py --dry-run

# 実際に移行
python scripts/migrate_jobs_to_items.py
```

すべての既存動画は「Inbox」フォルダに配置されます。その後、必要に応じてフォルダを作成して整理できます。


## Architecture

- **Frontend**: React + Next.js
- **Backend**: FastAPI (Python)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL
- **Audio Extraction**: yt-dlp
- **Speech-to-Text**: OpenAI Whisper API
- **LLM Correction**: OpenAI GPT-4o

## Prerequisites

- Docker & Docker Compose
- OpenAI API Key
- ffmpeg（大容量音声の自動圧縮/分割に使用）

> NOTE (WSL2 + Docker Desktop): WSL ディストリビューション側で `docker` が見えない場合、Docker Desktop の
> Settings → Resources → WSL Integration で使用中のディストリを有効化してから再試行してください。

## 注意点（利用前に確認）

- YouTube 側の制約:
	- メンバー限定、年齢制限、地域制限、削除済み/非公開、DRM 付きなどの動画は取得できない場合があります。
	- 配信アーカイブや極端に長い動画は、取得や変換に時間がかかり失敗率も上がります。
- 時間長の目安:
	- アプリ側の既定では「動画長の固定上限」は設けていません（環境変数で制御可能）。
	- ただし実運用では、長時間動画ほど処理時間・APIコスト・失敗時の再実行コストが増えます。
- OpenAI Whisper のアップロード制約:
	- API 制限（既定 25MB）を超える音声は自動で圧縮/分割します。
	- 分割時は境界付近の精度に影響することがあるため、最終結果の目視確認を推奨します。
- コストとレート制限:
	- 文字起こし/校正/Q&A は OpenAI API 課金対象です。
	- 短時間に大量投入すると API 側レート制限で遅延・リトライが発生します。
- ローカル起動時の注意:
	- run20 (backend) → run21 (frontend) の順で起動してください。
	- frontend は `.run_backend_port` を参照して接続先 API を決めるため、backend を先に起動しないと正しく接続できません。
- DB 接続の注意:
	- ローカル backend は `127.0.0.1:5432` に接続します。Docker の postgres が停止していると GUI は起動してもデータ取得が 500 になります。
	- 不整合時は `docker compose up -d postgres redis` の再実行を推奨します。
- 利用規約/法令順守:
	- YouTube 利用規約・著作権・社内ポリシーに従って利用してください。
	- 第三者コンテンツの無断配布・転載用途には使用しないでください。

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd 0106_cc-sdd
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=your_actual_api_key_here
```

### 3. Start Services

**Option 1: Backend + Frontend (Recommended)**

```bash
chmod +x start_app.sh
./start_app.sh --with-frontend
```

This will:
- Start all backend services (postgres, redis, api, worker)
- Install frontend dependencies if needed
- Start Next.js dev server in background
- Automatically open http://localhost:3000 in your browser

**Option 2: Backend only**

```bash
./start_app.sh
```

Then start frontend manually in another terminal:
```bash
cd frontend
npm install  # First time only
npm run dev
```

**Legacy method:**

```bash
docker compose up -d
```

If your environment still uses the legacy `docker-compose` command, you can run:

```bash
docker-compose up -d
```

### 4. Stop Services

**Stop all (backend + frontend):**
```bash
./stop_app.sh --all
```

**Stop backend only:**
```bash
./stop_app.sh
# or
docker compose down
```

### 5. Verify Services

```bash
docker compose ps
```

All services (postgres, redis, api, worker) should be running.

If you used `--with-frontend`, check the frontend log:
```bash
tail -f frontend.log
```

### 6. Access Application

- Frontend: http://localhost:3000 (Next.js UI)
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Development

### Build Backend EXE (Windows, PyInstaller)

ローカルバックエンドを単体EXEとしてビルドする場合は、以下を実行します。

```bat
run40_build_backend_exe.bat
```

成功すると以下が生成されます。

- `dist\\yt_transcripter_backend.exe`

起動方法:

```bat
dist\\yt_transcripter_backend.exe
```

必要に応じて環境変数で待受を変更できます。

- `BACKEND_HOST` (既定: `127.0.0.1`)
- `BACKEND_PORT` (既定: `8502`)

### Run Tests

```bash
# Create venv (PEP 668 environment requires venv)
python3 -m venv .venv
. .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt

# Run tests
pytest tests/
```

## Large File Support (over 25MB)

OpenAI の音声アップロード制限（デフォルト 25MB）を超える場合、ワーカーが自動で以下を行います：

- まず音声を **音声認識向けに圧縮**（mono / 16kHz / mp3 / 低ビットレート）
- それでも大きい場合は **分割**（チャンク間に短いオーバーラップを付与）
- 各チャンクを個別に文字起こしし、**タイムスタンプ（segments）をオフセットで連結**

### Environment Variables

- `MAX_UPLOAD_MB`：入力ファイルの防御的な上限（デフォルト `25`）
- `TARGET_UPLOAD_MB`：圧縮/分割後に目指す上限（安全マージン、デフォルト `24`）
- `AUDIO_BITRATE_KBPS`：圧縮時のビットレート（デフォルト `48`）
- `CHUNK_OVERLAP_SEC`：分割チャンクのオーバーラップ秒（デフォルト `0.8`）
- `MAX_SINGLE_CHUNK_SEC`：サイズが小さくても長時間音声を分割する閾値（デフォルト `900`）。長い音声を1リクエストで投げると末尾が欠ける場合があるため、安定化のために分割します。`0` 以下で無効化。

### Notes

- `ffmpeg` が PATH に無い場合、大容量ファイルの処理は失敗します。
- タイムスタンプは可能な場合に `verbose_json` の `segments` を保存し、SRT/VTT 出力に利用します。モデルやAPI仕様により segments が得られない場合は従来方式（均等割り当て）にフォールバックします。

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Start Celery Worker (Local Development)

**Windows:**
```bash
start_worker.bat
```

**Linux/Mac:**
```bash
chmod +x start_worker.sh
./start_worker.sh
```

**Or run directly:**
```bash
celery -A backend.worker worker --loglevel=info --concurrency=2
```

NOTE: Celery worker は自動リロードしません。バックエンドコードを変更した場合は worker を再起動してください。

### Stop Services

```bash
docker compose down
```

### Clean Up (including volumes)

```bash
docker compose down -v
```

## Project Structure

```
.
├── backend/              # Backend application code
│   ├── main.py          # FastAPI application entry point
│   ├── worker.py        # Celery worker tasks
│   ├── models.py        # SQLAlchemy database models
│   ├── database.py      # Database connection
│   ├── celery_config.py # Celery configuration
│   ├── routers/         # API route handlers
│   │   ├── jobs.py      # Job management endpoints
│   │   ├── export.py    # Export endpoints
│   │   ├── health.py    # Health check endpoint
│   │   └── schemas.py   # Pydantic request/response models
│   └── services/        # Business logic services
│       ├── audio_extractor.py          # YouTube audio extraction
│       ├── transcription_service.py    # Whisper API integration
│       ├── correction_service.py       # LLM correction
│       ├── export_service.py           # Export to TXT/SRT/VTT
│       └── job_manager.py              # Job lifecycle management
├── tests/               # Test suite
│   ├── test_audio_extractor.py
│   ├── test_transcription_service.py
│   ├── test_correction_service.py
│   ├── test_export_service.py
│   └── test_infrastructure.py
├── alembic/             # Database migrations
├── audio_files/         # Generated audio files (runtime)
├── .kiro/               # Spec-driven development files
│   └── specs/youtube-transcription/
│       ├── requirements.md   # Feature requirements
│       ├── design.md         # Technical design
│       └── tasks.md          # Implementation tasks
├── docker-compose.yml   # Docker orchestration
├── Dockerfile.api       # API container
├── Dockerfile.worker    # Worker container
├── requirements.txt     # Python dependencies
├── test_integration.py  # Integration test script
└── .env.example         # Environment template
```

## Implementation Status

### ✅ Phase 1: プロジェクト基盤構築 (Completed)
- Docker環境セットアップ
- データベーススキーマ設計
- タスクキューシステム構築

### ✅ Phase 2: コアサービス実装 (Completed)
- YouTube音声抽出サービス
- 文字起こしサービス
- LLM校正サービス
- エクスポートサービス

### ✅ Phase 3: バックエンドAPI構築 (Completed)
- FastAPIアプリケーションセットアップ
- ジョブ管理エンドポイント
- エクスポートエンドポイント
- ヘルスチェックエンドポイント

### ✅ Phase 5: 統合とテスト (Partially Completed)
- ワーカータスクの統合
- 統合テストスクリプト

### ✅ Phase 4: フロントエンド実装 (Completed)
- Next.js 14 + TypeScript + Tailwind CSS
- YouTube URL入力UI
- 進行状況表示UI
- 文字起こし結果表示UI
- LLM校正と前後比較UI
- エクスポート機能UI

## API Endpoints

### Job Management
- `POST /api/jobs/transcribe` - Create new transcription job
- `GET /api/jobs/{job_id}/status` - Get job status
- `GET /api/jobs/{job_id}/result` - Get transcription result
- `POST /api/jobs/{job_id}/correct` - Request LLM correction

### Export
- `GET /api/jobs/{job_id}/export?format=txt|srt|vtt` - Export transcript

Notes:
- 校正済み（`corrected_transcript` が存在）なら、エクスポートは校正後テキストが優先されます。
- SRT/VTT の `segments` はオリジナル transcript 側（`transcripts.segments_json`）から読み込みます。

### Monitoring
- `GET /health` - Health check
- `GET /` - Service info

## Testing

### Run Integration Tests

```bash
# Make sure API is running
python test_integration.py
```

### Run Unit Tests

```bash
pytest tests/ -v
```

## License

MIT
