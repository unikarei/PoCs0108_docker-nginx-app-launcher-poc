'use client'

import { useState } from 'react'
import { Folder } from '@/types/folder'

type Props = {
  isOpen: boolean
  folders: Folder[]
  onClose: () => void
  onSubmit: (targetFolderId: string) => void
}

export default function BulkMoveDialog({
  isOpen,
  folders,
  onClose,
  onSubmit,
}: Props) {
  const [selectedFolderId, setSelectedFolderId] = useState('')

  if (!isOpen) return null

  const renderFolderOptions = (folders: Folder[], depth: number = 0): JSX.Element[] => {
    const options: JSX.Element[] = []
    for (const folder of folders) {
      options.push(
        <option key={folder.id} value={folder.id}>
          {'　'.repeat(depth)}{folder.icon || '📁'} {folder.name}
        </option>
      )
      if (folder.children && folder.children.length > 0) {
        options.push(...renderFolderOptions(folder.children, depth + 1))
      }
    }
    return options
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFolderId) {
      alert('移動先フォルダを選択してください')
      return
    }
    onSubmit(selectedFolderId)
    setSelectedFolderId('')
  }

  const handleCancel = () => {
    setSelectedFolderId('')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-semibold mb-4">アイテムを移動</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              移動先フォルダ *
            </label>
            <select
              value={selectedFolderId}
              onChange={(e) => setSelectedFolderId(e.target.value)}
              className="input-field"
              required
            >
              <option value="">選択してください</option>
              {renderFolderOptions(folders)}
            </select>
          </div>

          <div className="flex gap-3 justify-end pt-4">
            <button
              type="button"
              onClick={handleCancel}
              className="btn-secondary px-6 py-2"
            >
              キャンセル
            </button>
            <button type="submit" className="btn-primary px-6 py-2">
              移動
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
