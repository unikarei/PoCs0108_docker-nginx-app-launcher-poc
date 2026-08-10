'use client'

import { useState } from 'react'

type Props = {
  isOpen: boolean
  parentId: string | null
  parentName?: string
  onClose: () => void
  onSubmit: (data: { name: string; description?: string; icon?: string }) => void
}

export default function FolderCreateDialog({
  isOpen,
  parentId,
  parentName,
  onClose,
  onSubmit,
}: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [icon, setIcon] = useState('📁')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      alert('フォルダ名を入力してください')
      return
    }
    onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      icon: icon || '📁',
    })
    setName('')
    setDescription('')
    setIcon('📁')
  }

  const handleCancel = () => {
    setName('')
    setDescription('')
    setIcon('📁')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-semibold mb-4">新規フォルダ作成</h2>
        
        {parentName && (
          <div className="mb-4 text-sm text-gray-600">
            親フォルダ: <span className="font-medium">{parentName}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              フォルダ名 *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
              placeholder="例: 重要な動画"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              アイコン
            </label>
            <input
              type="text"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              className="input-field"
              placeholder="📁"
            />
            <div className="mt-2 text-xs text-gray-500">
              絵文字を入力できます（例: 📁 📂 🎬 🎥 📝）
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              説明
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field"
              rows={3}
              placeholder="フォルダの説明（任意）"
            />
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
              作成
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
