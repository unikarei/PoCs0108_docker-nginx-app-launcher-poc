'use client'

import { useState } from 'react'

type Props = {
  isOpen: boolean
  onClose: () => void
  onSubmit: (tagName: string) => void
}

export default function BulkTagDialog({ isOpen, onClose, onSubmit }: Props) {
  const [tagName, setTagName] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!tagName.trim()) {
      alert('タグ名を入力してください')
      return
    }
    onSubmit(tagName.trim())
    setTagName('')
  }

  const handleCancel = () => {
    setTagName('')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-semibold mb-4">タグを追加</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              タグ名 *
            </label>
            <input
              type="text"
              value={tagName}
              onChange={(e) => setTagName(e.target.value)}
              className="input-field"
              placeholder="例: 重要, 会議, 学習"
              autoFocus
              required
            />
            <div className="mt-2 text-xs text-gray-500">
              既存のタグ名を入力すると、そのタグが追加されます
            </div>
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
              追加
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
