# Folder Tree Library - API Specification

## 概要

フォルダツリーライブラリのREST API仕様です。

すべてのAPIは `/api` プレフィックスで提供されます。
詳細なインタラクティブドキュメントは http://localhost:8000/docs で確認できます。

## Folder APIs

### GET /api/folders/tree

フォルダツリー全体を階層構造で取得します。

**Response:**
```json
{
  "folders": [
    {
      "id": "uuid",
      "name": "Inbox",
      "parent_id": null,
      "path": "/Inbox",
      "description": null,
      "color": null,
      "icon": "📥",
      "default_language": "ja",
      "default_model": "gpt-4o-mini-transcribe",
      "default_prompt": null,
      "default_qa_enabled": false,
      "default_output_format": "txt",
      "naming_template": null,
      "created_at": "2025-12-29T00:00:00Z",
      "updated_at": "2025-12-29T00:00:00Z",
      "item_count": {
        "queued": 5,
        "running": 2,
        "completed": 100,
        "failed": 3
      },
      "children": []
    }
  ]
}
```

### POST /api/folders/

新しいフォルダを作成します。

**Request Body:**
```json
{
  "name": "重要な動画",
  "parent_id": "parent-uuid",  // optional
  "description": "説明",  // optional
  "color": "#FF0000",  // optional
  "icon": "⭐",  // optional
  "default_language": "ja",  // optional
  "default_model": "gpt-4o-mini-transcribe",  // optional
  "default_prompt": "プロンプト",  // optional
  "default_qa_enabled": false,  // optional
  "default_output_format": "txt",  // optional
  "naming_template": "{title}_{date}"  // optional
}
```

**Response:** 201 Created
```json
{
  "id": "uuid",
  "name": "重要な動画",
  // ... (GET /api/folders/tree と同じ構造)
}
```

### GET /api/folders/{folder_id}

特定のフォルダを取得します。

**Response:** 200 OK
```json
{
  "id": "uuid",
  "name": "Inbox",
  // ... (GET /api/folders/tree と同じ構造)
}
```

### PUT /api/folders/{folder_id}

フォルダを更新します（名前、説明、色、アイコン）。

**Request Body:**
```json
{
  "name": "新しい名前",  // optional
  "description": "新しい説明",  // optional
  "color": "#00FF00",  // optional
  "icon": "🎬"  // optional
}
```

**Response:** 200 OK

### DELETE /api/folders/{folder_id}

空のフォルダを削除します。

**Response:** 200 OK
```json
{
  "folder_id": "uuid",
  "deleted": true
}
```

**Error:** 409 Conflict (フォルダが空でない場合)

### GET /api/folders/{folder_id}/settings

フォルダの既定値設定を取得します。

**Response:** 200 OK
```json
{
  "folder_id": "uuid",
  "folder_name": "Inbox",
  "default_language": "ja",
  "default_model": "gpt-4o-mini-transcribe",
  "default_prompt": null,
  "default_qa_enabled": false,
  "default_output_format": "txt",
  "naming_template": null
}
```

### PUT /api/folders/{folder_id}/settings

フォルダの既定値設定を更新します。

**Request Body:**
```json
{
  "default_language": "en",  // optional
  "default_model": "gpt-4o-transcribe",  // optional
  "default_prompt": "プロンプト",  // optional
  "default_qa_enabled": true,  // optional
  "default_output_format": "srt",  // optional
  "naming_template": "{title}_{date}"  // optional
}
```

## Item APIs

### GET /api/folders/{folder_id}/items

フォルダ内のアイテム一覧を取得します。

**Query Parameters:**
- `q` (string): キーワード検索
- `tag` (string): タグフィルタ
- `status` (string): ステータスフィルタ (queued/running/completed/failed)
- `sort` (string): ソート項目 (created_at/updated_at/duration_seconds/cost_usd)
- `order` (string): ソート順 (asc/desc)
- `limit` (integer): 取得件数 (default: 50, max: 500)
- `offset` (integer): オフセット (default: 0)

**Response:** 200 OK
```json
{
  "items": [
    {
      "id": "uuid",
      "folder_id": "folder-uuid",
      "job_id": "job-uuid",
      "title": "動画タイトル",
      "youtube_url": "https://youtube.com/watch?v=...",
      "description": null,
      "status": "completed",
      "progress": 100,
      "duration_seconds": 600,
      "cost_usd": 0.12,
      "tags": [
        {
          "id": "tag-uuid",
          "name": "会議",
          "color": "#FF0000"
        }
      ],
      "created_at": "2025-12-29T00:00:00Z",
      "updated_at": "2025-12-29T00:10:00Z"
    }
  ],
  "total": 100
}
```

### GET /api/items/search

全フォルダ横断検索を行います。

**Query Parameters:** (GET /api/folders/{folder_id}/items と同じ + folder_id)

### GET /api/items/{item_id}

特定のアイテムを取得します。

**Response:** 200 OK (items配列の要素と同じ構造)

### POST /api/items/{item_id}/move

アイテムを別のフォルダに移動します。

**Request Body:**
```json
{
  "target_folder_id": "target-folder-uuid"
}
```

**Response:** 200 OK
```json
{
  "status": "success",
  "message": "Item moved to folder 'XXX'",
  "item": { /* item data */ }
}
```

### DELETE /api/items/{item_id}

アイテムを削除します。

**Response:** 200 OK
```json
{
  "status": "success",
  "message": "Item deleted successfully",
  "item_id": "uuid",
  "job_id": "job-uuid"
}
```

### POST /api/items/{item_id}/tags

アイテムにタグを追加します。

**Request Body:**
```json
{
  "tag_name": "会議"
}
```

**Response:** 200 OK
```json
{
  "status": "success",
  "message": "Tag '会議' added to item",
  "tag": {
    "id": "tag-uuid",
    "name": "会議",
    "color": null
  }
}
```

### DELETE /api/items/{item_id}/tags/{tag_id}

アイテムからタグを削除します。

**Response:** 200 OK
```json
{
  "status": "success",
  "message": "Tag removed from item"
}
```

## Tag APIs

### GET /api/tags/

すべてのタグを取得します。

**Response:** 200 OK
```json
{
  "tags": [
    {
      "id": "uuid",
      "name": "会議",
      "color": "#FF0000",
      "created_at": "2025-12-29T00:00:00Z"
    }
  ]
}
```

### POST /api/tags/

新しいタグを作成します。

**Request Body:**
```json
{
  "name": "学習",
  "color": "#00FF00"  // optional
}
```

**Response:** 201 Created

### DELETE /api/tags/{tag_id}

タグを削除します（すべてのアイテムとの関連も削除されます）。

**Response:** 200 OK
```json
{
  "tag_id": "uuid",
  "deleted": true
}
```

## Bulk Operations

### POST /api/items/bulk/move

複数のアイテムを一括移動します。

**Request Body:**
```json
{
  "item_ids": ["uuid1", "uuid2", "uuid3"],
  "target_folder_id": "target-folder-uuid"
}
```

**Response:** 200 OK
```json
{
  "success_count": 3,
  "failed_count": 0,
  "failed_items": []
}
```

### POST /api/items/bulk/tag

複数のアイテムに一括でタグを追加します。

**Request Body:**
```json
{
  "item_ids": ["uuid1", "uuid2", "uuid3"],
  "tag_name": "重要"
}
```

**Response:** 200 OK

### POST /api/items/bulk/delete

複数のアイテムを一括削除します。

**Request Body:**
```json
{
  "item_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:** 200 OK
```json
{
  "success_count": 3,
  "failed_count": 0,
  "failed_items": []
}
```

## Error Responses

すべてのAPIは、エラー時に以下の形式でレスポンスを返します：

**400 Bad Request:**
```json
{
  "detail": "Invalid request parameters"
}
```

**404 Not Found:**
```json
{
  "detail": "Folder not found"
}
```

**409 Conflict:**
```json
{
  "detail": "Folder contains 5 items. Cannot delete non-empty folder."
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error",
  "message": "Error details..."
}
```

## Authentication

現在、認証は実装されていません。将来のバージョンで追加予定です。

## Rate Limiting

現在、レート制限は実装されていません。

## CORS

デフォルトですべてのオリジンを許可しています。本番環境では適切に制限してください。
