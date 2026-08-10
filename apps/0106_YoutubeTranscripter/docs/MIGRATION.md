# Folder Tree Library - Migration Guide

## 概要

このガイドでは、既存のJobsデータを新しいフォルダツリー構造（Items/Artifacts）に移行する方法を説明します。

## 移行の必要性

フォルダツリーライブラリ機能を使用するには、既存の動画データを新しいデータ構造に移行する必要があります：

- **Jobs** → **Items**: 動画メタデータをフォルダに所属させる
- **Transcript/CorrectedTranscript/QaResult** → **Artifacts**: 各種生成物をアーティファクトとして管理

## 前提条件

1. データベースマイグレーションが完了していること
   ```bash
   cd backend
   alembic upgrade head
   ```

2. データベースのバックアップを取得しておくこと（推奨）
   ```bash
   pg_dump youtube_transcription > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

## 移行手順

### 1. Dry Runで確認

まず、実際には変更せずに動作を確認します：

```bash
python scripts/migrate_jobs_to_items.py --dry-run
```

出力例：
```
Found 150 jobs to migrate
DRY RUN - No changes will be committed
[1/150] Migrated job abc-123 -> item DRY-RUN with 3 artifacts
...
✅ Dry run completed successfully!
Summary:
  Total jobs: 150
  Migrated: 150
  Skipped: 0
  Total artifacts created: 320
```

### 2. 実際の移行を実行

問題がなければ、実際に移行を実行します：

```bash
python scripts/migrate_jobs_to_items.py
```

### 3. 移行結果の確認

移行後、以下を確認します：

1. **Webインターフェースで確認**
   - http://localhost:3000 にアクセス
   - Library タブを開く
   - Inbox フォルダにすべての動画が表示されることを確認

2. **データベースで確認**
   ```sql
   -- Items数を確認
   SELECT COUNT(*) FROM items;
   
   -- Artifacts数を確認
   SELECT artifact_type, COUNT(*) FROM artifacts GROUP BY artifact_type;
   
   -- Inboxフォルダのアイテム数を確認
   SELECT f.name, COUNT(i.id) 
   FROM folders f 
   LEFT JOIN items i ON i.folder_id = f.id 
   WHERE f.name = 'Inbox'
   GROUP BY f.name;
   ```

## 移行される内容

### Items
各Jobに対して1つのItemが作成されます：
- `folder_id`: Inboxフォルダに配置
- `job_id`: 既存Jobへの参照
- `title`: Job.user_title または AudioFile.title
- `youtube_url`: Job.youtube_url
- `status`: Jobのstatusを変換（pending→queued, processing/transcribing/correcting→running等）
- `duration_seconds`: AudioFile.duration_seconds
- `file_size_bytes`: AudioFile.file_size_bytes

### Artifacts
各Jobの生成物に対してArtifactが作成されます：

1. **transcript**: Transcriptテーブルへの参照
   - `artifact_type`: 'transcript'
   - `transcript_id`: 元のTranscriptレコードID
   - メタデータ: language_detected, transcription_model, word_count, cost_usd

2. **proofread**: CorrectedTranscriptテーブルへの参照
   - `artifact_type`: 'proofread'
   - `corrected_transcript_id`: 元のCorrectedTranscriptレコードID
   - メタデータ: correction_model, correction_prompt, word_count, cost_usd

3. **qa**: QaResultテーブルへの参照（複数ある場合は各々）
   - `artifact_type`: 'qa'
   - `qa_result_id`: 元のQaResultレコードID
   - メタデータ: question, qa_model, cost_usd

## 再実行について

移行スクリプトは冪等性があり、何度実行しても安全です：
- 既にItemが存在するJobはスキップされます
- エラーが発生した場合はロールバックされます

## トラブルシューティング

### エラー: "No module named 'backend'"

スクリプトをプロジェクトルートから実行してください：
```bash
cd /path/to/0106_cc-sdd
python scripts/migrate_jobs_to_items.py
```

### エラー: "could not connect to server"

データベースが起動していることを確認してください：
```bash
docker compose ps postgres
docker compose up -d postgres
```

### 移行後にデータが表示されない

1. ブラウザのキャッシュをクリア
2. ページをリロード
3. ブラウザのコンソールでエラーを確認

### 移行を元に戻す

バックアップから復元：
```bash
dropdb youtube_transcription
createdb youtube_transcription
psql youtube_transcription < backup_YYYYMMDD_HHMMSS.sql
```

または、手動でItemsとArtifactsを削除（Jobsは保持）：
```sql
DELETE FROM artifacts;
DELETE FROM items;
```

## 移行後の運用

### 新しい動画の投入

新しく動画を投入する際は：
1. フォルダを選択（またはInboxに自動配置）
2. フォルダの既定値（言語、モデル等）が自動適用されます

### フォルダの整理

移行後、Inboxの動画を適切なフォルダに移動できます：
1. フォルダを作成（例: 「会議録」「学習用」等）
2. 動画を選択して一括移動
3. タグを付けて横断的に管理

## サポート

問題が発生した場合は、ログを確認してください：
```bash
# マイグレーションスクリプトのログ
python scripts/migrate_jobs_to_items.py --dry-run 2>&1 | tee migration.log

# アプリケーションログ
docker compose logs api
docker compose logs worker
```
