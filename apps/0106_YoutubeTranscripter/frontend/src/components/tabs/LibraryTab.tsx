'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import { AppSettings } from '@/lib/settings'
import { Folder, Item, Tag } from '@/types/folder'
import FolderTreePanel from '@/components/FolderTree/FolderTreePanel'
import FolderItemList, { SearchParams } from '@/components/FolderTree/FolderItemList'
import BulkActionsBar from '@/components/FolderTree/BulkActionsBar'
import FolderCreateDialog from '@/components/FolderTree/FolderCreateDialog'
import BulkMoveDialog from '@/components/FolderTree/BulkMoveDialog'
import BulkTagDialog from '@/components/FolderTree/BulkTagDialog'

type Props = {
  settings: AppSettings
  onSelectJob: (jobId: string) => void
}

export default function LibraryTab({ onSelectJob }: Props) {
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(new Set())
  const [tags, setTags] = useState<Tag[]>([])

  // Dialog states
  const [showCreateFolderDialog, setShowCreateFolderDialog] = useState(false)
  const [createFolderParentId, setCreateFolderParentId] = useState<string | null>(null)
  const [showBulkMoveDialog, setShowBulkMoveDialog] = useState(false)
  const [showBulkTagDialog, setShowBulkTagDialog] = useState(false)

  // Fetch folder tree
  const fetchFolders = async () => {
    try {
      const res = await apiClient.getFolderTree()
      setFolders(res.folders || [])
      
      // Auto-select first folder if none selected
      if (!selectedFolderId && res.folders && res.folders.length > 0) {
        setSelectedFolderId(res.folders[0].id)
      }
    } catch (err: any) {
      console.error('Failed to fetch folders:', err)
      setError(err?.response?.data?.detail || 'フォルダ取得に失敗しました')
    }
  }

  // Fetch items in selected folder
  const fetchItems = async (params?: SearchParams) => {
    if (!selectedFolderId) {
      setItems([])
      setTotal(0)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const res = await apiClient.getFolderItems(selectedFolderId, params)
      setItems(res.items || [])
      setTotal(res.total || 0)
      setSelectedItemIds(new Set())
    } catch (err: any) {
      console.error('Failed to fetch items:', err)
      setError(err?.response?.data?.detail || 'アイテム取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch tags
  const fetchTags = async () => {
    try {
      const res = await apiClient.getTags()
      setTags(res.tags || [])
    } catch (err: any) {
      console.error('Failed to fetch tags:', err)
    }
  }

  // Folder actions
  const handleCreateFolder = (parentId: string | null) => {
    setCreateFolderParentId(parentId)
    setShowCreateFolderDialog(true)
  }

  const handleSubmitCreateFolder = async (data: { name: string; description?: string; icon?: string }) => {
    try {
      await apiClient.createFolder({
        name: data.name,
        parent_id: createFolderParentId || undefined,
        description: data.description,
        icon: data.icon,
      })
      setShowCreateFolderDialog(false)
      fetchFolders()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'フォルダ作成に失敗しました')
    }
  }

  const handleEditFolder = (folderId: string) => {
    alert('フォルダ編集機能は未実装です')
  }

  const handleDeleteFolder = async (folderId: string) => {
    if (!window.confirm('このフォルダを削除しますか？（空のフォルダのみ削除可能）')) {
      return
    }
    try {
      await apiClient.deleteFolder(folderId)
      fetchFolders()
      if (selectedFolderId === folderId) {
        setSelectedFolderId(null)
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'フォルダ削除に失敗しました')
    }
  }

  // Item actions
  const handleToggleSelectItem = (itemId: string, checked: boolean) => {
    setSelectedItemIds((prev) => {
      const next = new Set(prev)
      if (checked) {
        next.add(itemId)
      } else {
        next.delete(itemId)
      }
      return next
    })
  }

  const handleSelectAllItems = (checked: boolean) => {
    if (checked) {
      setSelectedItemIds(new Set(items.map((item) => item.id)))
    } else {
      setSelectedItemIds(new Set())
    }
  }

  const handleItemClick = (itemId: string) => {
    const item = items.find((i) => i.id === itemId)
    if (item && item.job_id) {
      onSelectJob(item.job_id)
    }
  }

  const handleDeleteItem = async (itemId: string) => {
    if (!window.confirm('このアイテムを削除しますか？')) {
      return
    }
    try {
      await apiClient.deleteItem(itemId)
      fetchItems()
      fetchFolders() // Refresh counts
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'アイテム削除に失敗しました')
    }
  }

  // Bulk operations
  const moveItemsToFolder = async (itemIds: string[], targetFolderId: string, showSuccessAlert: boolean = false) => {
    const deduped = Array.from(new Set(itemIds))
    if (deduped.length === 0) return

    try {
      const res = await apiClient.bulkMoveItems(deduped, targetFolderId)
      setSelectedItemIds(new Set())
      fetchItems()
      fetchFolders()

      if (showSuccessAlert) {
        alert(`${res.success_count} 件のアイテムを移動しました`)
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || '移動に失敗しました')
    }
  }

  const handleBulkMove = () => {
    setShowBulkMoveDialog(true)
  }

  const handleSubmitBulkMove = async (targetFolderId: string) => {
    const itemIds = Array.from(selectedItemIds)
    setShowBulkMoveDialog(false)
    await moveItemsToFolder(itemIds, targetFolderId, true)
  }

  const handleDropItemsToFolder = async (targetFolderId: string, itemIds: string[]) => {
    await moveItemsToFolder(itemIds, targetFolderId, false)
  }

  const handleBulkTag = () => {
    setShowBulkTagDialog(true)
  }

  const handleSubmitBulkTag = async (tagName: string) => {
    const itemIds = Array.from(selectedItemIds)
    try {
      const res = await apiClient.bulkTagItems(itemIds, tagName)
      setShowBulkTagDialog(false)
      alert(`${res.success_count} 件のアイテムにタグを追加しました`)
      fetchItems()
      fetchTags()
    } catch (err: any) {
      alert(err?.response?.data?.detail || '一括タグ付けに失敗しました')
    }
  }

  const handleBulkDelete = async () => {
    const itemIds = Array.from(selectedItemIds)
    if (!window.confirm(`選択した ${itemIds.length} 件を削除しますか？`)) {
      return
    }
    try {
      const res = await apiClient.bulkDeleteItems(itemIds)
      alert(`${res.success_count} 件のアイテムを削除しました`)
      if (res.failed_count > 0) {
        console.error('Failed items:', res.failed_items)
      }
      fetchItems()
      fetchFolders()
    } catch (err: any) {
      alert(err?.response?.data?.detail || '一括削除に失敗しました')
    }
  }

  // Initial load
  useEffect(() => {
    fetchFolders()
    fetchTags()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Handle title update - update local state
  const handleTitleUpdate = (itemId: string, newTitle: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === itemId ? { ...item, title: newTitle } : item
      )
    )
  }

  const handleRatingUpdate = (itemId: string, rating: number) => {
    setItems((prev) => prev.map((item) => (item.id === itemId ? { ...item, rating } : item)))
  }

  // Load items when folder selected
  useEffect(() => {
    if (selectedFolderId) {
      fetchItems()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFolderId])

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-[350px_1fr] gap-4 h-[calc(100vh-200px)]">
        {/* Left: Folder Tree */}
        <FolderTreePanel
          folders={folders}
          selectedFolderId={selectedFolderId}
          onSelectFolder={setSelectedFolderId}
          onCreateFolder={handleCreateFolder}
          onEditFolder={handleEditFolder}
          onDeleteFolder={handleDeleteFolder}
          onDropItemsToFolder={handleDropItemsToFolder}
        />

        {/* Right: Item List */}
        <FolderItemList
          items={items}
          total={total}
          isLoading={isLoading}
          selectedItemIds={selectedItemIds}
          onToggleSelect={handleToggleSelectItem}
          onSelectAll={handleSelectAllItems}
          onItemClick={handleItemClick}
          onDeleteItem={handleDeleteItem}
          onSearch={fetchItems}
          onTitleUpdate={handleTitleUpdate}
          onRatingUpdate={handleRatingUpdate}
        />
      </div>

      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selectedItemIds.size}
        availableTags={tags}
        onBulkMove={handleBulkMove}
        onBulkTag={handleBulkTag}
        onBulkDelete={handleBulkDelete}
        onCancel={() => setSelectedItemIds(new Set())}
      />

      {/* Dialogs */}
      <FolderCreateDialog
        isOpen={showCreateFolderDialog}
        parentId={createFolderParentId}
        parentName={
          createFolderParentId
            ? folders.find((f) => f.id === createFolderParentId)?.name
            : undefined
        }
        onClose={() => setShowCreateFolderDialog(false)}
        onSubmit={handleSubmitCreateFolder}
      />

      <BulkMoveDialog
        isOpen={showBulkMoveDialog}
        folders={folders}
        onClose={() => setShowBulkMoveDialog(false)}
        onSubmit={handleSubmitBulkMove}
      />

      <BulkTagDialog
        isOpen={showBulkTagDialog}
        onClose={() => setShowBulkTagDialog(false)}
        onSubmit={handleSubmitBulkTag}
      />

      {error && (
        <div className="fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded shadow-lg">
          {error}
        </div>
      )}
    </>
  )
}
