# タスク計画: YouTube Transcription Web App

## 前提
- 実施順は spec -> architecture -> tasks -> implementation を厳守する。
- タスクは小さく分割し、差分を追跡可能にする。

## Phase 1: 基盤運用
### T1-1 依存可視化とヘルス
- [ ] 内容: DB/Redis/worker の可視化と /health の運用整備。
- [ ] 完了条件: 障害時に原因が判別できる。

### T1-2 起動スクリプト fail-fast
- [ ] 内容: run20/run21 の preflight とガードを整備。
- [ ] 完了条件: 依存不足時に曖昧失敗せず停止する。

### T1-3 Windows ワンショット EXE ビルド
- [x] 内容: PyInstaller でローカル FastAPI バックエンドを単体 EXE 化するための起動エントリと一発ビルドスクリプトを提供する。
- [x] 対象: backend/exe_main.py, run40_build_backend_exe.bat, README.md
- [x] 完了条件: run40_build_backend_exe.bat 実行で dist\yt_transcripter_backend.exe が生成される。

## Phase 2: ライブラリ運用
### T2-1 フォルダツリーと検索
- [ ] 内容: Folder/Item/Tag の表示、検索、フィルタを提供。
- [ ] 完了条件: フォルダ選択で一覧表示が更新される。

### T2-2 一括操作
- [ ] 内容: 一括移動・タグ付け・削除を API と UI で提供。
- [ ] 完了条件: 選択アイテムに対し bulk API が機能する。

### T2-3 ドラッグ&ドロップ移動
- [x] 内容: 右ペイン Item をドラッグし左ペイン Folder へドロップして移動できるようにする。
- [x] 対象: frontend/src/components/tabs/LibraryTab.tsx, frontend/src/components/FolderTree/FolderTreePanel.tsx, frontend/src/components/FolderTree/FolderItemList.tsx
- [x] 完了条件: ドロップで item の folder_id が更新され、一覧と件数が再取得される。

### T2-4 Note 装飾編集
- [x] 内容: Note タブで選択範囲に太字・黄色ハイライトの装飾を付与できるようにする。
- [x] 対象: frontend/src/components/tabs/ResultsTab.tsx
- [x] 完了条件: `**...**` と `==...==` の装飾を編集UIで付与でき、プレビューで反映される。

### T2-5 バッチキュー取消
- [x] 内容: Batch タブで投入済みの待機中/実行中ジョブを取消できるようにする。
- [x] 対象: backend/routers/jobs.py, backend/services/job_manager.py, backend/worker.py, frontend/src/components/tabs/BatchTab.tsx
- [x] 完了条件: Queue 一覧から取消操作ができ、対象ジョブが canceled として停止し、後続の完了更新で上書きされない。

## Phase 3: 品質維持
### T3-1 回帰確認
- [ ] 内容: 既存の一括移動・選択操作・削除操作に回帰がないことを確認。
- [ ] 完了条件: 主要操作が従来どおり動作する。

## Phase 4: 運用安定化
### T4-1 Alembic version_num 桁数拡張
- [x] 内容: `alembic_version.version_num` を `varchar(32)` から十分な長さへ拡張し、長い revision ID でも migrate が失敗しないようにする。
- [x] 対象: alembic/versions/20260531_001_add_job_canceled_status.py
- [x] 完了条件: revision ID `20260531_001_add_job_canceled_status` の適用時に `value too long for type character varying(32)` が発生しない。

## 今回の対象タスク
- [x] T1-3 Windows ワンショット EXE ビルド
- [x] T2-3 ドラッグ&ドロップ移動
- [x] T2-4 Note 装飾編集
- [x] T2-5 バッチキュー取消
