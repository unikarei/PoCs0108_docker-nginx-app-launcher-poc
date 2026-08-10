# 動画時間制限の解除について

## 変更内容

60分の動画時間制限を削除し、無制限で長時間動画を処理できるようになりました。

## 設定方法

### デフォルト動作
- **制限なし**: 何時間の動画でも処理可能（デフォルト）

### 制限を設定したい場合

`.env` ファイルに以下を追加：

```bash
# 動画時間制限（秒単位）
# 0 = 制限なし（デフォルト）
MAX_VIDEO_DURATION_SECONDS=0

# 例：2時間（7200秒）に制限する場合
# MAX_VIDEO_DURATION_SECONDS=7200

# 例：4時間（14400秒）に制限する場合  
# MAX_VIDEO_DURATION_SECONDS=14400
```

## 変更されたファイル

1. **backend/services/audio_extractor.py**
   - 60分（3600秒）のハードコード制限を削除
   - 環境変数 `MAX_VIDEO_DURATION_SECONDS` で制御
   - デフォルト値: 0（制限なし）

2. **docker-compose.yml**
   - `api` と `worker` サービスに環境変数を追加
   - `.env` ファイルから設定を読み込み

3. **.env.example**
   - 設定例を追加

## 処理の仕組み

### 長時間動画の自動分割

起動手順.mdに記載されている通り、25MB以上の音声ファイルは自動的に圧縮・分割されます：

```bash
# 設定（任意）
MAX_UPLOAD_MB=25                  # 入力ファイルの防御的上限
TARGET_UPLOAD_MB=24              # 圧縮/分割後の目標上限
AUDIO_BITRATE_KBPS=48            # 圧縮ビットレート
CHUNK_OVERLAP_SEC=0.8            # 分割オーバーラップ秒
MAX_SINGLE_CHUNK_SEC=900         # 長時間音声を分割する閾値（15分）
```

### 処理例

- **60分の動画**: 自動的に分割処理され、各チャンクが文字起こしされた後、結合されます
- **2時間の動画**: 同様に自動分割・処理・結合
- **4時間以上**: 処理時間はかかりますが、問題なく処理可能

## 注意事項

1. **処理時間**: 動画が長いほど処理時間も長くなります
2. **OpenAI API費用**: Whisper APIの使用料金は処理時間に比例します
3. **ストレージ**: 長時間動画の音声ファイルは大容量になります
4. **メモリ**: 非常に長い動画の場合、サーバーのメモリ使用量に注意

## トラブルシューティング

### 処理が途中で止まる場合

```bash
# Celeryワーカーのログを確認
docker compose logs worker

# タイムアウト設定の調整（backend/celery_config.py）
task_soft_time_limit = 3600  # 1時間から必要に応じて増やす
```

### メモリ不足の場合

```bash
# Docker Desktopのメモリ制限を増やす
# Settings → Resources → Memory
```

## 動作確認

1. サービスを再起動：
```bash
docker compose down
docker compose up -d --build
```

2. 長時間動画でテスト：
   - http://localhost:3000 にアクセス
   - 60分以上の動画URLを入力
   - 処理が正常に開始されることを確認

## ログ確認

```bash
# APIログ
docker compose logs -f api

# Workerログ
docker compose logs -f worker
```
