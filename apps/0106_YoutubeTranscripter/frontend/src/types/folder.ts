/**
 * Folder Tree Library Types
 */

export type Tag = {
  id: string
  name: string
  color?: string | null
  created_at: string
}

export type FolderItemCount = {
  queued: number
  running: number
  completed: number
  failed: number
}

export type Folder = {
  id: string
  name: string
  parent_id?: string | null
  path: string
  description?: string | null
  color?: string | null
  icon?: string | null
  default_language?: string | null
  default_model?: string | null
  default_prompt?: string | null
  default_qa_enabled?: boolean
  default_output_format?: string | null
  naming_template?: string | null
  created_at: string
  updated_at: string
  item_count: FolderItemCount
  children: Folder[]
}

export type FolderTreeResponse = {
  folders: Folder[]
}

export type Item = {
  id: string
  folder_id: string
  job_id: string
  title?: string | null
  youtube_url?: string | null
  description?: string | null
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress?: number | null
  duration_seconds?: number | null
  cost_usd?: number | null
  rating?: number | null
  tags: Tag[]
  created_at: string
  updated_at: string
}

export type ItemListResponse = {
  items: Item[]
  total: number
}

export type BulkOperationResult = {
  success_count: number
  failed_count: number
  failed_items: Array<{
    item_id: string
    error: string
  }>
}

export type FolderSettings = {
  default_language?: string | null
  default_model?: string | null
  default_prompt?: string | null
  default_qa_enabled?: boolean | null
  default_output_format?: string | null
  naming_template?: string | null
}

export type FolderSettingsResponse = FolderSettings & {
  folder_id: string
  folder_name: string
}

export type FolderCreate = {
  name: string
  parent_id?: string | null
  description?: string | null
  color?: string | null
  icon?: string | null
  default_language?: string | null
  default_model?: string | null
  default_prompt?: string | null
  default_qa_enabled?: boolean | null
  default_output_format?: string | null
  naming_template?: string | null
}

export type FolderUpdate = {
  name?: string | null
  description?: string | null
  color?: string | null
  icon?: string | null
}
