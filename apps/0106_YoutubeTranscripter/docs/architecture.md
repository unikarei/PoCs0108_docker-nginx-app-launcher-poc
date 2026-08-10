# アーキテクチャ設計: YouTube Transcription Web App

## 1. 設計方針
- UI、API、非同期ワーカー、永続化を明確に分離する。
- API は同期レスポンスとジョブ投入、重い処理はワーカーで実行する。
- ローカル運用時の失敗は preflight と health で早期に可視化する。

## 2. 論理コンポーネント
1. Frontend (Next.js)
- バッチ投入、キュー監視、結果閲覧、設定 UI、ライブラリ UI を担当する。

2. API (FastAPI)
- ジョブ作成、状態取得、結果取得、エクスポート、フォルダ/タグ/ノート API を提供する。
- 依存障害時は明示的な HTTP エラーを返す。

3. Worker (Celery)
- 音声抽出、前処理（圧縮/分割）、文字起こし、マージ、校正、Q&A を実行する。

4. Storage
- PostgreSQL: jobs/items/folders/tags/transcripts 等の永続データ。
- Redis: Celery broker/result backend。
- audio_files/: 実行時の音声中間ファイル。

5. Migration
- Alembic によるスキーマ管理。

## 3. データモデル境界
- Job: 外部入力 URL と処理ライフサイクルの主軸。
- Item/Folder/Tag: ライブラリ管理の表示・整理軸。
- Transcript/CorrectedTranscript/QaResult: 成果物。
- API ルータは DB 直接更新を最小化し、サービス層を経由する。

## 4. 実行プロファイル
1. Docker フルスタック
- docker-compose.yml で postgres, redis, migrate, api, worker, frontend を起動。

2. ローカル no-Docker（API/Frontend ホスト実行）
- run20: FastAPI を起動し、DB/Redis/worker を preflight で検査。
- run21: Next.js を起動し、backend /health が healthy であることを確認。
- DB/Redis/worker は Docker コンテナを併用可能。

## 5. 主要フロー
1. ジョブ投入
- UI -> POST /api/jobs/transcribe -> Job/Item 作成 -> Celery キュー投入。

2. 非同期処理
- worker.transcription_task が抽出/前処理/認識/保存を実行し進捗更新。

3. 二次処理
- proofread_task と qa_task が追加入力に応じて成果物を保存。

5. バッチキュー取消
- UI -> POST /api/jobs/{job_id}/cancel -> service が Job を canceled に更新 -> Celery revoke で未実行/実行中タスクの停止を試みる。
- worker は Job が canceled に遷移していたら後続保存や完了更新を行わず終了する。

6. ライブラリ移動（UI）
- UI は status/result/list API をポーリングし表示更新。

5. ライブラリ移動（UI）
7. ノート装飾（UI）
- フロントは bulk move API を利用し、移動後に Item 一覧と Folder 件数を再取得する。

6. ノート装飾（UI）
- Note 編集欄で選択範囲を記法（`**...**`, `==...==`）でラップする。
- プレビュー描画時は HTML エスケープ後に記法を変換し、XSS を防止する。

## 6. 障害処理方針
- DB 接続不可: API は 503 を返却。
- キュー投入不可: API は 503 を返却し、対象ジョブを failed に更新。
- worker 不在: health は degraded を返し、run20/run21 のガードで検知。
- ユーザー取消: API は Job を canceled に更新し、worker は canceled 状態を終端として扱う。

## 7. 運用境界ルール
- config/起動スクリプトに業務ロジックを入れない。
- routers はリクエスト境界、services は業務処理、worker は非同期実行に限定する。
- UI は API レスポンスを表示し、サーバ側状態を再計算しない。
